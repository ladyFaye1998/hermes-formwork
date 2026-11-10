"""Packet invariants: real PDFs, exact evidence, review gates and persistence."""
import base64
import hashlib
import contextvars
import time
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfReader

from formwork.store import PacketStore, PacketError
from pdf_fixtures import make_form, make_source


def upload_item(path, name=None):
    return {"name": name or path.name, "data": base64.b64encode(path.read_bytes()).decode()}


@pytest.fixture
def packet(tmp_path):
    first = make_form(tmp_path / "registration.pdf")
    second = make_form(tmp_path / "organization.pdf")
    source = make_source(tmp_path / "facts.pdf")
    store = PacketStore(tmp_path / "state")
    state = store.upload([upload_item(first), upload_item(second), upload_item(source)])
    return store, state, first, source


def field(state, name="full_name", form_index=0):
    return next(x for x in state["forms"][form_index]["fields"] if x["id"] == name)


def proposal(state, value="Alex Rowan", quote="Full name: Alex Rowan", form_index=0):
    return {"formId": state["forms"][form_index]["id"], "fieldId": "full_name", "value": value,
            "sourceId": state["sources"][0]["id"], "page": 1, "quote": quote, "reason": "Named in the supporting facts"}


def update(state, value="Alex Rowan", form_index=0, field_id="full_name"):
    return {"formId": state["forms"][form_index]["id"], "fieldId": field_id, "value": value, "origin": "user"}


def test_import_persists_real_geometry_and_immutable_originals(packet):
    store, state, original, _ = packet
    assert len(state["forms"]) == 2
    assert len(state["sources"]) == 1
    assert field(state)["page"] == 1
    assert field(state, "company")["page"] == 2
    assert state["forms"][0]["pages"][0]["number"] == 1
    assert 0 <= field(state)["rect"][1] < field(state)["rect"][3] <= 792
    assert "storedPath" not in state["forms"][0]
    assert PacketStore(store.root).packet() == state
    source_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    assert state["forms"][0]["sha256"] == source_hash


def test_duplicate_filenames_receive_distinct_storage_ids(tmp_path):
    form = make_form(tmp_path / "form.pdf")
    store = PacketStore(tmp_path / "state")
    result = store.upload([upload_item(form), upload_item(form)])
    assert result["forms"][0]["name"] == result["forms"][1]["name"]
    assert result["forms"][0]["id"] != result["forms"][1]["id"]
    assert len(list((store.root / "documents").glob("*.pdf"))) == 2


@pytest.mark.parametrize("bad", [
    {"name": "../escape.pdf", "data": "AA=="},
    {"name": "escape\\name.pdf", "data": "AA=="},
    {"name": "form.txt", "data": "AA=="},
    {"name": "form.pdf", "data": "not-base64!"},
])
def test_bad_upload_rolls_back_the_whole_batch(tmp_path, bad):
    form = make_form(tmp_path / "form.pdf")
    store = PacketStore(tmp_path / "state")
    before = store.packet()
    with pytest.raises(PacketError):
        store.upload([upload_item(form), bad])
    assert store.packet() == before
    assert not list((store.root / "documents").glob("*.pdf"))
    assert not list(store.root.glob(".upload-*"))


def test_source_backed_answer_requires_explicit_review_before_export(packet):
    store, state, _, _ = packet
    current = store.apply_proposals([proposal(state)], expected_revision=state["revision"])
    assert field(current)["origin"] == "model"
    assert field(current)["evidence"]["quote"] == "Full name: Alex Rowan"
    with pytest.raises(PacketError, match="Review every"):
        store.export()
    reviewed = store.update_values([update(current)])
    assert field(reviewed)["origin"] == "user"
    assert field(reviewed)["evidence"]["quote"] == "Full name: Alex Rowan"


@pytest.mark.parametrize("change", [
    {"quote": "Full name: Invented Person", "value": "Invented Person"},
    {"page": 0}, {"page": 99}, {"sourceId": "not-imported"},
    {"fieldId": "not-a-field"}, {"value": "Mallory Unknown"},
])
def test_fabricated_or_mismatched_evidence_cannot_change_state(packet, change):
    store, state, _, _ = packet
    bad = {**proposal(state), **change}
    with pytest.raises(PacketError):
        store.apply_proposals([bad], expected_revision=state["revision"])
    assert store.packet() == state


def test_stale_extraction_and_later_reruns_preserve_user_corrections(packet):
    store, state, _, _ = packet
    reviewed = store.update_values([update(state, "User Chosen Name")])
    with pytest.raises(PacketError, match="changed while"):
        store.apply_proposals([proposal(state)], expected_revision=state["revision"])
    current = store.apply_proposals([proposal(reviewed)], expected_revision=reviewed["revision"])
    assert field(current)["value"] == "User Chosen Name"
    assert field(current)["origin"] == "user"
    assert PacketStore(store.root).packet() == current


def test_changing_a_sourced_answer_clears_stale_citation(packet):
    store, state, _, _ = packet
    proposed = store.apply_proposals([proposal(state)])
    changed = store.update_values([update(proposed, "User Chosen Name")])
    assert field(changed)["evidence"] is None
    assert field(changed)["origin"] == "user"


def test_conflicting_sources_stay_blank_until_an_explicit_choice(tmp_path):
    form = make_form(tmp_path / "form.pdf")
    source = make_source(tmp_path / "facts.pdf", "Full name: Alex Rowan\nFull name: Blair Rowan")
    store = PacketStore(tmp_path / "state")
    state = store.upload([upload_item(form), upload_item(source)])
    first = proposal(state)
    second = proposal(state, value="Blair Rowan", quote="Full name: Blair Rowan")
    conflict = store.apply_proposals([first, second])
    assert field(conflict)["value"] == ""
    assert field(conflict)["status"] == "conflict"
    assert len(field(conflict)["alternatives"]) == 2
    with pytest.raises(PacketError):
        store.export()
    chosen = store.update_values([{**second, "origin": "user"}])
    assert field(chosen)["value"] == "Blair Rowan"
    assert field(chosen)["evidence"]["quote"] == second["quote"]
    assert "alternatives" not in field(chosen)


def test_export_reopens_editable_originals_without_mutating_sources(packet):
    store, state, original, _ = packet
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (store.root / "documents").glob("*.pdf")}
    store.update_values([update(state, form_index=0), update(state, form_index=1),
                         update(state, True, form_index=0, field_id="agree"),
                         update(state, True, form_index=1, field_id="agree")])
    output = store.export()
    pdfs = [x for x in output["exports"] if x["name"].endswith(".pdf")]
    assert len(pdfs) == 2
    for item in pdfs:
        result = PdfReader(item["path"])
        assert len(result.pages) == 2
        assert result.get_fields()["full_name"]["/V"] == "Alex Rowan"
        assert item["verified"] is True
        assert any(a.get_object().get("/Subtype") == "/Widget" for p in result.pages for a in p.get("/Annots", []))
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (store.root / "documents").glob("*.pdf")}
    assert before == after
    assert any(x["name"].endswith(".zip") for x in output["exports"])
    archive = next(x for x in output["exports"] if x["name"].endswith(".zip"))
    with zipfile.ZipFile(archive["path"]) as bundle:
        assert not any(n.startswith("sources/") for n in bundle.namelist())
        manifest = json.loads(bundle.read("review.json"))
        assert all("path" not in item for item in manifest["files"])


def test_source_attachments_require_explicit_opt_in_and_keep_exact_bytes(packet):
    store, state, _, source = packet
    store.update_values([update(state, form_index=0), update(state, form_index=1),
                         update(state, True, form_index=0, field_id="agree"),
                         update(state, True, form_index=1, field_id="agree")])
    result = store.export(include_sources=True)
    archive = next(x for x in result["exports"] if x["name"].endswith(".zip"))
    with zipfile.ZipFile(archive["path"]) as bundle:
        sources = [n for n in bundle.namelist() if n.startswith("sources/")]
        assert len(sources) == 1
        assert bundle.read(sources[0]) == source.read_bytes()
        assert json.loads(bundle.read("review.json"))["includeSources"] is True
    with pytest.raises(PacketError):
        store.export(include_sources="true")


def test_preview_reflects_current_saved_values(packet):
    store, state, _, _ = packet
    blank = store.render(form_id=state["forms"][0]["id"], page=1)
    store.update_values([update(state)])
    filled = store.render(form_id=state["forms"][0]["id"], page=1)
    assert filled["dataUrl"].startswith("data:image/png;base64,")
    assert filled["width"] > 0 and filled["height"] > 0
    assert blank["dataUrl"] != filled["dataUrl"]


def test_partial_value_batch_is_atomic(packet):
    store, state, _, _ = packet
    with pytest.raises(PacketError):
        store.update_values([update(state), update(state, field_id="missing")])
    assert store.packet() == state


def wait_for_job(runtime, root, job_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        result = runtime.job_status(root, job_id)
        if result["status"] != "running":
            return result
        time.sleep(0.01)
    pytest.fail("The extraction job did not reach a terminal state.")


def test_host_bound_model_job_inherits_context_and_persists_results(packet, monkeypatch):
    from formwork import runtime
    store, state, _, _ = packet
    scope = contextvars.ContextVar("test_formwork_scope")
    scope.set("selected-profile")
    calls = []

    def complete(**kwargs):
        calls.append((scope.get(), kwargs))
        return SimpleNamespace(parsed={"proposals": [proposal(state)]}, model="test-model", provider="test-provider")

    handlers = {}
    ctx = SimpleNamespace(llm=SimpleNamespace(complete_structured=complete),
                          register_rpc=lambda name, handler: handlers.update({name: handler}))
    monkeypatch.setattr(runtime, "data_root", lambda: store.root)
    runtime.register_extraction(ctx)
    started = handlers["extract"]({})
    finished = wait_for_job(runtime, store.root, started["jobId"])
    assert finished["status"] == "completed"
    assert calls[0][0] == "selected-profile"
    assert calls[0][1]["purpose"] == "formwork.extract"
    assert not {"provider", "model", "agent_id", "profile"}.intersection(calls[0][1])
    assert field(store.packet())["value"] == "Alex Rowan"
    assert field(store.packet())["origin"] == "model"


def test_failed_host_model_job_returns_no_secret_response_and_keeps_packet(packet, monkeypatch):
    from formwork import runtime
    store, state, _, _ = packet

    def complete(**kwargs):
        raise RuntimeError("private-provider-response sk-do-not-expose")

    handlers = {}
    ctx = SimpleNamespace(llm=SimpleNamespace(complete_structured=complete),
                          register_rpc=lambda name, handler: handlers.update({name: handler}))
    monkeypatch.setattr(runtime, "data_root", lambda: store.root)
    runtime.register_extraction(ctx)
    started = handlers["extract"]({})
    finished = wait_for_job(runtime, store.root, started["jobId"])
    assert finished["status"] == "failed"
    assert "sk-do-not-expose" not in str(finished)
    assert "private-provider-response" not in str(finished)
    assert store.packet() == state


def test_new_packet_archives_everything_without_erasing_files_or_reusing_revision(packet):
    store, state, _, _ = packet
    store.update_values([update(state, form_index=0), update(state, form_index=1),
                         update(state, True, form_index=0, field_id="agree"),
                         update(state, True, form_index=1, field_id="agree")])
    exported = store.export()
    previous = store.packet()
    original_files = {str(p): p.read_bytes() for p in (store.root / "documents").glob("*.pdf")}
    export_files = {item["path"]: Path(item["path"]).read_bytes() for item in exported["exports"]}
    current = store.new_packet()
    assert current["id"] != previous["id"]
    assert current["revision"] > previous["revision"]
    assert current["forms"] == current["sources"] == current["exports"] == []
    archived = [json.loads(p.read_text(encoding="utf-8")) for p in (store.root / "archives").glob("*.json")]
    assert archived[0]["id"] == previous["id"]
    assert len(archived[0]["forms"]) == 2
    assert archived[0]["forms"][0]["fields"][0]["origin"] == "user"
    assert {p: Path(p).read_bytes() for p in original_files} == original_files
    assert {p: Path(p).read_bytes() for p in export_files} == export_files
    with pytest.raises(PacketError, match="changed while"):
        store.apply_proposals([proposal(state)], expected_revision=state["revision"])
    assert store.packet() == current
    assert PacketStore(store.root).packet() == current
