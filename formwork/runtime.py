"""Host-bound, asynchronous extraction. The model facade is supplied by Hermes."""
from __future__ import annotations

import contextvars
import json
import threading
import uuid
from pathlib import Path

from .store import PacketStore, PacketError


def data_root():
    from hermes_constants import get_hermes_home
    return Path(get_hermes_home()) / "plugin-data" / "formwork"


def job_status(root, job_id):
    if not isinstance(job_id, str) or len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
        raise PacketError("Unknown extraction job.")
    path = Path(root) / "jobs" / (job_id + ".json")
    if not path.is_file():
        raise PacketError("Unknown extraction job.")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_job(root, job_id, body):
    directory = Path(root) / "jobs"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (job_id + ".json")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"jobId": job_id, **body}), encoding="utf-8")
    temporary.replace(path)


def register_extraction(ctx):
    slots = threading.BoundedSemaphore(1)

    def extract(params, *, session_id=None, **kwargs):
        if not slots.acquire(blocking=False):
            raise PacketError("An extraction is already running. Wait for it to finish.")
        root = data_root()
        store = PacketStore(root)
        job_id = uuid.uuid4().hex
        _write_job(root, job_id, {"status": "running"})

        def run():
            try:
                spec = store.extraction_input()
                result = ctx.llm.complete_structured(
                    instructions=spec["instructions"], input=spec["input"], json_schema=spec["json_schema"],
                    schema_name="formwork.proposals", purpose="formwork.extract", temperature=0,
                    max_tokens=6000, timeout=120)
                if not isinstance(result.parsed, dict) or not isinstance(result.parsed.get("proposals"), list):
                    raise PacketError("The model did not return a valid proposal list. Your packet is unchanged.")
                packet = store.apply_proposals(result.parsed["proposals"], expected_revision=spec["revision"])
                _write_job(root, job_id, {"status": "completed", "revision": packet["revision"],
                                         "model": result.model, "provider": result.provider})
            except Exception as exc:
                # Do not return provider responses or tokens to the frontend.
                error = str(exc) if isinstance(exc, PacketError) else "Model extraction failed. Check the configured Hermes model and try again; your packet was preserved."
                _write_job(root, job_id, {"status": "failed", "error": error})
            finally:
                slots.release()
        try:
            threading.Thread(target=contextvars.copy_context().run, args=(run,), daemon=True).start()
        except BaseException:
            slots.release()
            _write_job(root, job_id, {"status": "failed", "error": "Extraction could not start."})
            raise
        return {"jobId": job_id, "status": "running"}

    ctx.register_rpc("extract", extract)
