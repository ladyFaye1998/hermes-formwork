"""LOCAL VISUAL QA ONLY. Uses real PacketStore and API routes; no model emulator.

Run from the repository root with the test dependencies installed:
    .venv/Scripts/python tests/ui/server.py
Build browser.mjs first with tests/ui/build.mjs. This harness does not prove
Hermes Desktop integration, native grants, RPC ownership or native downloads.
"""
from __future__ import annotations

import base64
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dashboard import plugin_api
from formwork.store import PacketStore
from pdf_fixtures import make_form, make_source

ROOT = REPO / ".cache" / "ui-harness"
INPUT = ROOT / "input"
HOME = ROOT / "state"
INPUT.mkdir(parents=True, exist_ok=True)
make_form(INPUT / "workshop-registration.pdf")
make_form(INPUT / "second-registration.pdf")
make_source(INPUT / "supporting-facts.pdf")
plugin_api.data_root = lambda: HOME
app = FastAPI()
app.include_router(plugin_api.router, prefix="/api/plugins/formwork")
client = TestClient(app)


class Handler(BaseHTTPRequestHandler):
    def send(self, status, data, mime="application/json"):
        if not isinstance(data, bytes):
            data = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parts = urlsplit(self.path)
        if parts.path.startswith("/api/plugins/formwork/"):
            response = client.get(self.path)
            return self.send(response.status_code, response.content, response.headers.get("content-type", "application/json"))
        if parts.path == "/test/folder":
            return self.send(200, {"ok": True, "entries": [{"name": p.name, "path": p.name, "isDirectory": False} for p in INPUT.glob("*.pdf")], "truncated": False})
        if parts.path == "/test/read":
            name = parse_qs(parts.query).get("name", [""])[0]
            path = INPUT / name
            if path.parent != INPUT or not path.is_file():
                return self.send(404, {"ok": False, "message": "Unknown test fixture."})
            return self.send(200, {"ok": True, "url": "data:application/pdf;base64," + base64.b64encode(path.read_bytes()).decode()})
        if parts.path == "/test/download":
            name = parse_qs(parts.query).get("path", [""])[0]
            path = Path(name).resolve()
            current = PacketStore(HOME).packet()
            if str(path) not in {str(Path(x["path"]).resolve()) for x in current["exports"]}:
                return self.send(404, {"error": "Unknown exported test file."})
            return self.send(200, path.read_bytes(), "application/octet-stream")
        if parts.path == "/browser.mjs":
            return self.send(200, (ROOT / "browser.mjs").read_bytes(), "text/javascript")
        if parts.path == "/":
            return self.send(200, b'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Formwork - isolated UI QA</title><style>html,body,#root{height:100%;margin:0}body{overflow:hidden}#notice{height:25px;box-sizing:border-box;background:#27222f;color:#f0e6f4;font:10px system-ui;padding:5px 12px;letter-spacing:.4px}#root{height:calc(100% - 25px)}</style></head><body><div id="notice">ISOLATED VISUAL QA - real PDF backend, synthetic test fixtures - no model simulation; not native Hermes proof</div><div id="root"></div><script type="module" src="/browser.mjs"></script></body></html>''', "text/html")
        self.send(404, {"error": "Not found."})

    def do_POST(self):
        if not self.path.startswith("/api/plugins/formwork/"):
            return self.send(404, {"error": "Not found."})
        size = int(self.headers.get("Content-Length", "0"))
        response = client.post(self.path, content=self.rfile.read(size), headers={"Content-Type": "application/json"})
        self.send(response.status_code, response.content, response.headers.get("content-type", "application/json"))

    def log_message(self, fmt, *args):
        if "200" not in str(args):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    print("Isolated Formwork UI QA: http://127.0.0.1:8791", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8791), Handler).serve_forever()
