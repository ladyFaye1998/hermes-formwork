"""Host-bound, asynchronous extraction. The model facade is supplied by Hermes."""
from __future__ import annotations

import contextvars
import json
import logging
import re
import threading
import time
import traceback
import uuid
from pathlib import Path

from .store import PacketStore, PacketError

log = logging.getLogger(__name__)


def data_root():
    from hermes_constants import get_hermes_home
    return Path(get_hermes_home()) / "plugin-data" / "formwork"


def job_status(root, job_id):
    if not isinstance(job_id, str) or len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
        raise PacketError("Unknown extraction job.")
    path = Path(root) / "jobs" / (job_id + ".json")
    if not path.is_file():
        raise PacketError("Unknown extraction job.")
    for attempt in range(8):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(0.025 * (attempt + 1))


def _write_job(root, job_id, body):
    directory = Path(root) / "jobs"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (job_id + ".json")
    temporary = path.with_suffix(".tmp")
    try:
        temporary.write_text(json.dumps({"jobId": job_id, **body}), encoding="utf-8")
        for attempt in range(8):
            try:
                temporary.replace(path)
                break
            except PermissionError:
                if attempt == 7:
                    raise
                # Windows readers or virus scanners can briefly hold the target.
                time.sleep(0.025 * (attempt + 1))
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _failure_category(exc):
    """Classify without copying exception messages, response bodies, or URLs."""
    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    if status in (401, 403):
        return "authentication"
    if status == 429:
        return "rate_limit"
    if isinstance(status, int) and status >= 500:
        return "provider_unavailable"
    if isinstance(status, int) and 400 <= status < 500:
        return "provider_rejected_input"
    if isinstance(exc, PacketError):
        return "packet_validation"
    if "Timeout" in name:
        return "timeout"
    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return "runtime_dependency"
    if "Trust" in name or "Auth" in name:
        return "model_configuration"
    if "Validation" in name:
        return "response_validation"
    if isinstance(exc, (TypeError, AttributeError, KeyError)):
        return "integration"
    if isinstance(exc, ValueError):
        return "request_or_response_validation"
    if isinstance(exc, PermissionError):
        return "local_file_access"
    return "model_or_runtime"


def _safe_diagnostic_token(value):
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value):
        return value
    return None


def _failure_diagnostic(exc):
    """Return selected standard metadata; never copy a provider message/body."""
    diagnostic = {"exceptionClass": _safe_diagnostic_token(type(exc).__name__),
                  "category": _failure_category(exc)}
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and not isinstance(status, bool):
        diagnostic["status_code"] = status
    body = getattr(exc, "body", None)
    error = body.get("error", body) if isinstance(body, dict) else {}
    error = error if isinstance(error, dict) else {}
    for key in ("code", "param", "type"):
        value = getattr(exc, key, None) or error.get(key)
        if key == "param" and isinstance(value, str):
            value = value.replace("[", ".").replace("]", "")
        safe_value = _safe_diagnostic_token(value)
        if safe_value is not None:
            diagnostic[key] = safe_value
    # An SDK exception can retain the original request. Select only its model
    # identifier, never messages, images, headers, URLs, or credential fields.
    try:
        request = getattr(exc, "request", None)
        content = getattr(request, "content", None)
        if isinstance(content, bytes) and len(content) <= 4 * 1024 * 1024:
            request_body = json.loads(content)
            model = request_body.get("model") if isinstance(request_body, dict) else None
            if isinstance(model, str):
                parts = model.split("/")
                if parts and all(_safe_diagnostic_token(part) for part in parts):
                    diagnostic["requestModelParts"] = parts
    except Exception:
        pass
    diagnostic["frames"] = [{"file": Path(frame.filename).name,
                              "function": _safe_diagnostic_token(frame.name) or "filtered"}
                             for frame in traceback.extract_tb(exc.__traceback__)[-8:]]
    return diagnostic


def register_extraction(ctx):
    ctx.register_auxiliary_task(
        "formwork_extract", display_name="Formwork extraction",
        description="Read original form labels and propose source-backed answers.",
        inherit_from="vision", defaults={"timeout": 120})
    slots = threading.BoundedSemaphore(1)

    def extract(params, *, session_id=None, **kwargs):
        if not slots.acquire(blocking=False):
            raise PacketError("An extraction is already running. Wait for it to finish.")
        try:
            root = data_root()
            store = PacketStore(root)
            job_id = uuid.uuid4().hex
            _write_job(root, job_id, {"status": "running"})
        except BaseException:
            # The worker does not exist yet, so it cannot release our slot.
            slots.release()
            raise

        def run():
            try:
                spec = store.extraction_input()
                result = ctx.llm.complete_structured(
                    instructions=spec["instructions"], input=spec["input"], json_schema=spec["json_schema"],
                    schema_name="formwork.proposals", purpose="formwork.extract", task="formwork_extract", temperature=0,
                    max_tokens=6000, timeout=120)
                if not isinstance(result.parsed, dict) or not isinstance(result.parsed.get("proposals"), list):
                    raise PacketError("The model did not return a valid proposal list. Your packet is unchanged.")
                packet = store.apply_proposals(result.parsed["proposals"], expected_revision=spec["revision"])
                _write_job(root, job_id, {"status": "completed", "revision": packet["revision"],
                                         "model": result.model, "provider": result.provider})
            except Exception as exc:
                # Do not return provider responses or tokens to the frontend.
                diagnostic = _failure_diagnostic(exc)
                exception_class = type(exc).__name__
                log.warning("Formwork extraction failed: %s", exception_class)
                error = str(exc) if isinstance(exc, PacketError) else "Model extraction failed. Check the configured Hermes model and try again; your packet was preserved."
                _write_job(root, job_id, {"status": "failed", "error": error,
                                         "diagnostic": diagnostic})
            finally:
                slots.release()
        try:
            threading.Thread(target=contextvars.copy_context().run, args=(run,), daemon=True).start()
        except BaseException:
            slots.release()
            try:
                _write_job(root, job_id, {"status": "failed", "error": "Extraction could not start."})
            except Exception:
                pass  # Preserve the startup error if job storage also fails.
            raise
        return {"jobId": job_id, "status": "running"}

    ctx.register_rpc("extract", extract)
