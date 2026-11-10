"""Formwork's authenticated Hermes backend namespace."""
import hashlib
import importlib
import importlib.util
from pathlib import Path
import sys

from fastapi import APIRouter, HTTPException

# The dashboard loader imports this file independently of the Python plugin.
# Load only our sibling package under our own path-specific module namespace;
# never alter sys.path, Hermes modules, or another plugin's imports.
_package_dir = Path(__file__).resolve().parents[1] / "formwork"
_package_name = "_formwork_local_" + hashlib.sha256(str(_package_dir).encode()).hexdigest()[:12]
if _package_name not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_package_name, _package_dir / "__init__.py", submodule_search_locations=[str(_package_dir)])
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_package_name] = _module
    try:
        _spec.loader.exec_module(_module)
    except BaseException:
        sys.modules.pop(_package_name, None)
        raise
_store_module = importlib.import_module(_package_name + ".store")
_runtime_module = importlib.import_module(_package_name + ".runtime")
PacketStore, PacketError = _store_module.PacketStore, _store_module.PacketError
data_root, job_status = _runtime_module.data_root, _runtime_module.job_status

router = APIRouter()


def _call(method, *args, **kwargs):
    try:
        return getattr(PacketStore(data_root()), method)(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/packet")
def packet():
    return _call("packet")


@router.post("/new")
def new_packet(body: dict):
    if body.get("archiveCurrent") is not True:
        raise HTTPException(status_code=400, detail="Confirm that the current packet should be archived before starting a new one.")
    return _call("new_packet")


@router.post("/upload")
def upload(body: dict):
    return _call("upload", body.get("files"))


@router.post("/values")
def values(body: dict):
    return _call("update_values", body.get("updates"))


@router.post("/extract")
def extract():
    raise HTTPException(status_code=409, detail="Start extraction through the Formwork Desktop workspace's host-bound plugin RPC.")


@router.get("/jobs/{job_id}")
def job(job_id: str):
    try:
        return job_status(data_root(), job_id)
    except PacketError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/render")
def render(formId: str = None, sourceId: str = None, page: int = 1):
    return _call("render", form_id=formId, source_id=sourceId, page=page)


@router.post("/export")
def export(body: dict = None):
    return _call("export", include_sources=(body or {}).get("includeSources", False))
