"""Conservative, local AcroForm inspection, filling and verification.

Page numbers are zero based. ``rect`` uses the PDF's bottom-left coordinates;
``display_rect`` uses top-left coordinates after CropBox translation and /Rotate.
Field ids are fully-qualified PDF field names, not model-generated identifiers.

This first version handles text, checkboxes and single-select combo boxes. Empty
signature widgets are preserved as manual work. It does not repair malformed
field trees, sign, flatten, OCR or submit documents.
``verified`` concerns the requested values and their PDF representations. It is
not a statement that the supplied facts are true or that an application is ready
to submit; ``complete`` separately reports required-field completeness.
"""

from __future__ import annotations

import hashlib
import io
import math
import os
import re
import tempfile
import threading
from functools import wraps
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject, DecodedStreamObject, DictionaryObject, IndirectObject,
    NameObject, NullObject, NumberObject, TextStringObject,
)


MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_PAGES = 100
MAX_FIELDS = 1000
MIN_FONT_SIZE = 6.0
MAX_RENDER_PIXELS = 32_000_000
_PDFIUM_LOCK = threading.RLock()


class FormworkError(ValueError):
    """A document or request cannot be processed without guessing."""


def _serialized_pdfium(function):
    """PDFium is process-global and cannot safely run on concurrent threads."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        with _PDFIUM_LOCK:
            return function(*args, **kwargs)
    return wrapped

def _obj(value: Any) -> Any:
    return value.get_object() if hasattr(value, "get_object") else value


def _identity(value: Any) -> tuple:
    ref = value if isinstance(value, IndirectObject) else getattr(value, "indirect_reference", None)
    return ("ref", ref.idnum, ref.generation) if ref is not None else ("direct", id(value))


def _plain(value: Any) -> Any:
    value = _obj(value)
    if isinstance(value, (list, tuple)):
        return [_plain(x) for x in value]
    if value is None:
        return ""
    return str(value)


def _reader(path: str | Path) -> PdfReader:
    path = Path(path)
    if not path.is_file():
        raise FormworkError("The PDF file does not exist.")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise FormworkError("PDF exceeds the 32 MB processing limit.")
    if re.search(rb"/ByteRange\s*\[", path.read_bytes()):
        raise FormworkError("Digitally signed PDFs are unsupported; supply an unsigned original.")
    try:
        reader = PdfReader(str(path), strict=True)
    except Exception as exc:
        raise FormworkError("The file is not a readable, structurally valid PDF.") from exc
    if reader.is_encrypted:
        raise FormworkError("Encrypted PDFs are unsupported; supply an unlocked copy.")
    if len(reader.pages) > MAX_PAGES:
        raise FormworkError("PDF exceeds the 100 page processing limit.")
    return reader


def _inherit(node: Any, key: str, default: Any = None) -> Any:
    seen: set[tuple] = set()
    while node is not None:
        if _identity(node) in seen:
            raise FormworkError("The form contains a cyclic parent relationship.")
        seen.add(_identity(node))
        node = _obj(node)
        if key in node:
            return _obj(node[key])
        node = node.get("/Parent")
    return default


def _qualified_name(node: Any) -> str:
    names: list[str] = []
    seen: set[tuple] = set()
    while node is not None:
        if _identity(node) in seen:
            raise FormworkError("The form contains a cyclic parent relationship.")
        seen.add(_identity(node))
        node = _obj(node)
        if "/T" in node:
            names.append(str(node["/T"]))
        node = node.get("/Parent")
    return ".".join(reversed(names))


def _ancestors(node: Any) -> set[tuple]:
    seen: set[tuple] = set()
    while node is not None:
        ident = _identity(node)
        if ident in seen:
            raise FormworkError("The form contains a cyclic parent relationship.")
        seen.add(ident)
        node = _obj(node).get("/Parent")
    return seen


def _page_geometry(page: Any, index: int) -> dict:
    crop = [float(v) for v in page.cropbox]
    if len(crop) != 4 or not all(math.isfinite(v) for v in crop):
        raise FormworkError("Invalid PDF page bounds.")
    w, h = crop[2] - crop[0], crop[3] - crop[1]
    media = [float(v) for v in page.mediabox]
    if crop[0] < media[0] - .5 or crop[1] < media[1] - .5 or crop[2] > media[2] + .5 or crop[3] > media[3] + .5:
        raise FormworkError("CropBox extends outside MediaBox; field placement cannot be verified.")
    rotation = int(page.get_inherited("/Rotate", 0)) % 360
    if w <= 0 or h <= 0 or rotation not in (0, 90, 180, 270):
        raise FormworkError("Unsupported PDF page geometry or rotation.")
    if float(page.get("/UserUnit", 1)) != 1:
        raise FormworkError("PDF pages with a custom UserUnit are unsupported.")
    return {"index": index, "width": h if rotation in (90, 270) else w,
            "height": w if rotation in (90, 270) else h,
            "pdf_width": w, "pdf_height": h, "rotation": rotation,
            "crop_box": crop, "fields": []}


def _display_rect(rect: list[float], geometry: dict) -> list[float]:
    cx, cy, _, _ = geometry["crop_box"]
    x0, y0, x1, y1 = rect[0] - cx, rect[1] - cy, rect[2] - cx, rect[3] - cy
    w, h, rot = geometry["pdf_width"], geometry["pdf_height"], geometry["rotation"]
    if rot == 0:
        return [x0, h - y1, x1, h - y0]
    if rot == 90:
        return [y0, x0, y1, x1]
    if rot == 180:
        return [w - x1, y0, w - x0, y1]
    return [h - y1, w - x1, h - y0, w - x0]


def _catalog(reader: Any) -> tuple[dict, dict[str, Any], dict[str, list[Any]]]:
    pages = [_page_geometry(p, i) for i, p in enumerate(reader.pages)]
    result = {"supported": True, "page_count": len(pages), "pages": pages,
              "fields": [], "manual_fields": [], "warnings": [], "rejections": []}
    root = reader.root_object if isinstance(reader, PdfWriter) else reader.trailer["/Root"]
    acro = _obj(root.get("/AcroForm", {}))
    if "/XFA" in acro:
        result["rejections"].append("XFA forms are unsupported.")
    if "/Perms" in root:
        result["rejections"].append("Certified or permission-controlled PDFs are unsupported.")
    if "/OpenAction" in root or "/AA" in root or "/JavaScript" in _obj(root.get("/Names", {})):
        result["rejections"].append("PDF document actions or JavaScript are unsupported.")
    canonical: dict[str, Any] = {}
    visited: set[tuple] = set()

    def walk(ref: Any, prefix: str = "") -> None:
        ident = _identity(ref)
        if ident in visited:
            raise FormworkError("A field appears more than once in the canonical field tree.")
        visited.add(ident)
        node = _obj(ref)
        if not isinstance(node, dict):
            raise FormworkError("The canonical field tree contains a non-dictionary object.")
        partial = str(node.get("/T", ""))
        name = ".".join(x for x in (prefix, partial) if x)
        kids = list(_obj(node.get("/Kids", [])))
        named_kids = [k for k in kids if "/T" in _obj(k)]
        if named_kids:
            if len(named_kids) != len(kids):
                raise FormworkError("A field mixes child fields with unnamed widgets.")
            for child in kids:
                if _identity(ref) not in _ancestors(child):
                    raise FormworkError("A child field has no matching canonical parent link.")
                walk(child, name)
            return
        if not name:
            raise FormworkError("An unnamed terminal field cannot be addressed safely.")
        if name in canonical:
            raise FormworkError(f"Duplicate fully-qualified field name: {name}.")
        canonical[name] = ref
        if len(canonical) > MAX_FIELDS:
            raise FormworkError("PDF exceeds the 1,000 field processing limit.")
        for child in kids:
            if _identity(ref) not in _ancestors(child):
                raise FormworkError(f"Widget parent relationship is broken for {name}.")

    for ref in _obj(acro.get("/Fields", [])):
        walk(ref)
    widget_map: dict[str, list[Any]] = {name: [] for name in canonical}
    for page_no, page in enumerate(reader.pages):
        for ref in _obj(page.get("/Annots", [])):
            widget = _obj(ref)
            if widget.get("/Subtype") != "/Widget":
                continue
            name = _qualified_name(ref)
            if not name or name not in canonical:
                result["rejections"].append("An orphan widget is absent from the canonical field tree.")
                continue
            if _identity(canonical[name]) not in _ancestors(ref):
                result["rejections"].append(f"Ambiguous widget and canonical field share the name {name}.")
                continue
            rect = [float(x) for x in widget.get("/Rect", [])]
            if len(rect) != 4 or not all(math.isfinite(x) for x in rect) or rect[2] <= rect[0] or rect[3] <= rect[1]:
                result["rejections"].append(f"Field {name} has invalid widget bounds.")
                continue
            geom = pages[page_no]
            display_rect = _display_rect(rect, geom)
            if display_rect[0] < -0.5 or display_rect[1] < -0.5 or display_rect[2] > geom["width"] + .5 or display_rect[3] > geom["height"] + .5:
                result["rejections"].append(f"Field {name} extends outside the visible page.")
            if int(widget.get("/F", 0)) & (1 | 2 | 32):
                result["rejections"].append(f"Field {name} has an invisible, hidden or non-viewable widget.")
            if "/AA" in widget or "/A" in widget:
                result["rejections"].append(f"Field {name} has interactive actions that cannot be verified locally.")
            widget_map[name].append((ref, {"page": page_no, "rect": rect, "display_rect": display_rect,
                                                "rotation": geom["rotation"]}))

    for name, ref in canonical.items():
        node = _obj(ref)
        ft = str(_inherit(ref, "/FT", ""))
        flags = int(_inherit(ref, "/Ff", 0))
        signature_value = _inherit(ref, "/V") if ft == "/Sig" else None
        signed = (signature_value is not None and not isinstance(signature_value, NullObject)
                  and signature_value != "")
        field = {"id": name, "name": name, "label": str(_inherit(ref, "/TU", name)),
                 "type": "unsupported", "value": "" if ft == "/Sig" else _plain(_inherit(ref, "/V", "")),
                 "raw_value": "" if ft == "/Sig" else _plain(_inherit(ref, "/V", "")), "options": [],
                 "required": bool(flags & 2), "read_only": bool(flags & 1),
                 "multiline": bool(flags & 4096), "max_length": _inherit(ref, "/MaxLen"),
                 "flags": flags, "widgets": [meta for _, meta in widget_map[name]]}
        if "/AA" in node or "/A" in node:
            result["rejections"].append(f"Field {name} has calculation or interactive actions.")
        if ft == "/Sig":
            if signed:
                result["rejections"].append("Digitally signed PDFs are unsupported; supply an unsigned original.")
            field["type"] = "signature"
            field["read_only"] = True
            field["manual"] = True
            result["warnings"].append(f"Manual signature still needed for {field['label']}.")
        elif ft == "/Tx":
            field["type"] = "text"
            if flags & (8192 | 1048576 | 33554432):
                result["rejections"].append(f"Password, file-select or rich text field {name} is unsupported.")
        elif ft == "/Btn" and not flags & (32768 | 65536):
            field["type"] = "checkbox"
            states: set[str] = set()
            for widget_ref, _ in widget_map[name]:
                ap = _obj(_obj(widget_ref).get("/AP", {}))
                normal = _obj(ap.get("/N", {}))
                if not isinstance(normal, dict):
                    result["rejections"].append(f"Checkbox {name} has no usable appearance states.")
                    continue
                local = {str(k) for k in normal if str(k) != "/Off"}
                if len(local) != 1 or "/Off" not in normal:
                    result["rejections"].append(f"Checkbox {name} has ambiguous appearance states.")
                states.update(local)
            if len(states) != 1:
                result["rejections"].append(f"Checkbox {name} does not have one consistent checked value.")
            field["on_value"] = next(iter(states), "/Yes")
            field["value"] = str(field["raw_value"]) not in ("", "/Off", "Off")
        elif ft == "/Ch" and flags & 131072 and not flags & (2097152 | 262144):
            field["type"] = "choice"
            for item in _inherit(ref, "/Opt", []):
                item = _obj(item)
                if isinstance(item, list):
                    if len(item) != 2:
                        result["rejections"].append(f"Choice field {name} has malformed options.")
                        continue
                    value, label = map(str, item)
                else:
                    value = label = str(item)
                field["options"].append({"value": value, "label": label})
            if not field["options"] or len({o["value"] for o in field["options"]}) != len(field["options"]):
                result["rejections"].append(f"Choice field {name} has missing or duplicate option values.")
        else:
            result["rejections"].append(f"Unsupported field type for {name}: {ft or 'unknown'}.")
        if not field["widgets"]:
            result["rejections"].append(f"Canonical field {name} has no visible page widget.")
        else:
            field.update(field["widgets"][0])
            if ft != "/Sig":
                for widget in field["widgets"]:
                    pages[widget["page"]]["fields"].append({**field, **widget, "widgets": field["widgets"]})
        result["manual_fields" if ft == "/Sig" else "fields"].append(field)
    if not canonical:
        result["rejections"].append("No canonical AcroForm fields were found. Scans and flat PDFs are unsupported.")
    result["rejections"] = list(dict.fromkeys(result["rejections"]))
    result["supported"] = not result["rejections"]
    return result, canonical, widget_map


def inspect_pdf(path: str | Path) -> dict:
    """Return JSON-safe geometry and unique canonical fields, with scope refusals."""
    try:
        reader = _reader(path)
        result, _, _ = _catalog(reader)
        result["sha256"] = _sha256(path)
        return result
    except FormworkError as exc:
        return {"supported": False, "pages": [], "fields": [], "manual_fields": [], "warnings": [],
                "rejections": [str(exc)], "page_count": 0}


def _sha256(path: str | Path) -> str:
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def extract_text(path: str | Path) -> list[dict]:
    """Extract verbatim per-page text from a PDF; no OCR or silent truncation."""
    reader = _reader(path)
    return [{"page": index, "text": page.extract_text() or ""} for index, page in enumerate(reader.pages)]


def _pdfium():
    try:
        import pypdfium2
    except ImportError as exc:
        raise FormworkError("PDF rendering requires the pypdfium2 dependency.") from exc
    return pypdfium2


@_serialized_pdfium
def render_page(path: str | Path, page: int, scale: float = 1.4) -> bytes:
    """Render a complete page, including interactive form appearances, as PNG."""
    _reader(path)
    if isinstance(page, bool) or not isinstance(page, int) or page < 0:
        raise FormworkError("Page must be a zero-based, nonnegative integer.")
    if not isinstance(scale, (int, float)) or not math.isfinite(scale) or not .25 <= scale <= 4:
        raise FormworkError("Render scale must be between 0.25 and 4.")
    document = _pdfium().PdfDocument(str(path))
    try:
        document.init_forms()
        if page >= len(document):
            raise FormworkError("Requested page is outside the document.")
        pdf_page = document[page]
        try:
            width, height = pdf_page.get_size()
            if width * height * scale * scale > MAX_RENDER_PIXELS:
                raise FormworkError("Rendered page exceeds the 32 megapixel limit.")
            bitmap = pdf_page.render(scale=scale, draw_annots=True)
            try:
                output = io.BytesIO()
                bitmap.to_pil().save(output, format="PNG")
                return output.getvalue()
            finally:
                bitmap.close()
        finally:
            pdf_page.close()
    finally:
        document.close()


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _appearance_fingerprint(widget_ref: Any) -> tuple:
    normal = _obj(_obj(_obj(widget_ref).get("/AP", {})).get("/N", {}))
    def stream_fingerprint(stream):
        stream = _obj(stream)
        if not hasattr(stream, "get_data"):
            return None
        return (hashlib.sha256(stream.get_data()).hexdigest(), str(stream.get("/BBox")), str(stream.get("/Matrix")))
    if hasattr(normal, "get_data"):
        return (stream_fingerprint(normal),)
    if isinstance(normal, dict):
        return tuple((str(k), stream_fingerprint(v)) for k, v in sorted(normal.items()))
    return ()


@_serialized_pdfium
def _appearance_check(widget_ref: Any, expected: str | bool, field: dict) -> dict:
    """Read/render the actual saved AP as a standalone Form XObject, not /V."""
    widget = _obj(widget_ref)
    normal = _obj(_obj(widget.get("/AP", {})).get("/N"))
    if field["type"] == "checkbox":
        state = field["on_value"] if expected else "/Off"
        if str(widget.get("/AS", "")) != state or not isinstance(normal, dict) or state not in normal:
            return {"ok": False, "reason": "Checkbox appearance state does not match its value."}
        appearance = _obj(normal[state])
    else:
        appearance = normal
    if not hasattr(appearance, "get_data") or not appearance.get_data():
        return {"ok": False, "reason": "Missing or empty normal appearance stream."}
    bbox = [float(v) for v in appearance.get("/BBox", [])]
    if len(bbox) != 4 or not all(math.isfinite(v) for v in bbox) or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
        return {"ok": False, "reason": "Appearance has invalid bounds."}
    width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if width * height * 1.4 ** 2 > MAX_RENDER_PIXELS:
        return {"ok": False, "reason": "Field appearance exceeds the rendering limit."}
    probe = PdfWriter()
    page = probe.add_blank_page(width=width, height=height)
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): DictionaryObject({
        NameObject("/FW"): probe._add_object(appearance.clone(probe)),
    })})
    content = DecodedStreamObject()
    content.set_data(f"q 1 0 0 1 {-bbox[0]} {-bbox[1]} cm /FW Do Q".encode("ascii"))
    page[NameObject("/Contents")] = probe._add_object(content)
    buffer = io.BytesIO()
    probe.write(buffer)
    document = _pdfium().PdfDocument(buffer.getvalue())
    try:
        page = document[0]
        try:
            bitmap = page.render(scale=1.4)
            bitmap.close()
            text_page = page.get_textpage()
            try:
                text = text_page.get_text_bounded(left=0, bottom=0, right=width, top=height)
                if field["type"] != "checkbox":
                    wanted = str(expected)
                    if field["type"] == "choice":
                        wanted = next(o["label"] for o in field["options"] if o["value"] == wanted)
                    if _normalized_text(text) != _normalized_text(wanted):
                        return {"ok": False, "reason": "Visible appearance text differs from the requested value or is clipped.",
                                "visible_text": text}
                    font_sizes = [float(x) for x in re.findall(rb"[-\w.+]+\s+([\d.]+)\s+Tf", appearance.get_data())]
                    if wanted and font_sizes and min(font_sizes) < MIN_FONT_SIZE:
                        return {"ok": False, "reason": "Value would require text smaller than 6 pt.", "font_size": min(font_sizes)}
                    for index in range(text_page.count_chars()):
                        char = text_page.get_text_range(index, 1)
                        if not char.strip():
                            continue
                        left, bottom, right, top = text_page.get_charbox(index)
                        if left < -.75 or bottom < -.75 or right > width + .75 or top > height + .75:
                            return {"ok": False, "reason": "Text glyph bounds overflow the field appearance."}
                return {"ok": True, "visible_text": text, "rendered": True}
            finally:
                text_page.close()
        finally:
            page.close()
    finally:
        document.close()


def _validated_values(info: dict, values: dict) -> dict[str, str | bool]:
    if not isinstance(values, dict) or not values:
        raise FormworkError("Provide at least one field value.")
    fields = {f["id"]: f for f in info["fields"]}
    unknown = set(values) - set(fields)
    if unknown:
        raise FormworkError("Unknown field ids: " + ", ".join(sorted(map(str, unknown))))
    normalized: dict[str, str | bool] = {}
    for name, value in values.items():
        field = fields[name]
        if field["type"] == "checkbox":
            if not isinstance(value, bool):
                raise FormworkError(f"Checkbox {name} requires true or false.")
        else:
            if not isinstance(value, str):
                raise FormworkError(f"Field {name} requires a text value.")
            if any(ord(char) > 126 or ord(char) < 32 and char not in "\n\r\t" for char in value):
                raise FormworkError(f"Field {name} contains unsupported characters. This release only verifies printable ASCII text.")
            if not field["multiline"] and any(c in value for c in "\n\r\t"):
                raise FormworkError(f"Field {name} is a single-line field.")
            if field["max_length"] is not None and len(value) > int(field["max_length"]):
                raise FormworkError(f"Field {name} exceeds its maximum length of {field['max_length']}.")
            if field["type"] == "choice" and value not in {o["value"] for o in field["options"]}:
                raise FormworkError(f"Field {name} requires one of its declared option values.")
            if field["type"] == "choice":
                label = next(o["label"] for o in field["options"] if o["value"] == value)
                if any(ord(char) < 32 or ord(char) > 126 for char in label):
                    raise FormworkError(f"Field {name} has an unsupported non-ASCII option label.")
        if field["read_only"] and value != field["value"]:
            raise FormworkError(f"Field {name} is read-only.")
        normalized[name] = value
    return normalized


def fill_pdf(source: str | Path, output: str | Path, values: dict) -> dict:
    """Fill an editable copy, verify saved values/widgets/APs, then publish it.

    The source is never written. Existing output paths and source aliases are
    refused. Verification failure removes the private candidate and publishes
    no output. Unsupported fonts/overflow cannot silently count as verified.
    """
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or output.exists():
        raise FormworkError("Choose a new output path; originals and existing files are never overwritten.")
    if output.suffix.lower() != ".pdf" or not output.parent.is_dir():
        raise FormworkError("Output must be a new .pdf file in an existing directory.")
    reader = _reader(source)
    original_hash = _sha256(source)
    info, _, original_widgets = _catalog(reader)
    if not info["supported"]:
        raise FormworkError(" ".join(info["rejections"]))
    normalized = _validated_values(info, values)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    # No reattach_fields(): a misleading duplicate field must remain a refusal.
    _, writer_fields, writer_widgets = _catalog(writer)
    fields = {f["id"]: f for f in info["fields"]}
    encoded = {name: (fields[name]["on_value"] if value else "/Off")
               if fields[name]["type"] == "checkbox" else value for name, value in normalized.items()}
    # Widget APs live in widget-local PDF coordinates. Current pypdf versions
    # swap the AP's width/height when the PAGE is rotated, even though the
    # viewer already rotates the whole page/widget. Generate in the original
    # coordinate system, then restore the exact page rotation declarations.
    rotations = [page.get("/Rotate") for page in writer.pages]
    for page in writer.pages:
        page[NameObject("/Rotate")] = NumberObject(0)
    try:
        writer.update_page_form_field_values(None, encoded, auto_regenerate=False)
        # A combo may use a display label different from its exported /V.
        for name, value in normalized.items():
            field = fields[name]
            if field["type"] != "choice":
                continue
            label = next(o["label"] for o in field["options"] if o["value"] == value)
            if label != value:
                writer.update_page_form_field_values(None, {name: label}, auto_regenerate=False)
                _obj(writer_fields[name])[NameObject("/V")] = TextStringObject(value)
                for ref, _ in writer_widgets[name]:
                    if "/V" in _obj(ref):
                        _obj(ref)[NameObject("/V")] = TextStringObject(value)
    finally:
        for page, original_rotation in zip(writer.pages, rotations):
            if original_rotation is None:
                page.pop(NameObject("/Rotate"), None)
            else:
                page[NameObject("/Rotate")] = original_rotation
    candidate_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".formwork-", suffix=".pdf", dir=output.parent, delete=False) as stream:
            candidate_path = stream.name
            writer.write(stream)
        saved = _reader(candidate_path)
        after, _, saved_widgets = _catalog(saved)
        saved_fields = {f["id"]: f for f in after["fields"]}
        canonical_fields = saved.get_fields() or {}
        checks = {"source_unchanged": _sha256(source) == original_hash,
                  "page_count": after["page_count"] == info["page_count"],
                  "page_content_preserved": all(
                      (before.get_contents().get_data() if before.get_contents() is not None else b"") ==
                      (new.get_contents().get_data() if new.get_contents() is not None else b"")
                      for before, new in zip(reader.pages, saved.pages)),
                  "page_geometry_preserved": all(
                      all(before[k] == new[k] for k in ("width", "height", "rotation", "crop_box"))
                      for before, new in zip(info["pages"], after["pages"])),
                  "field_tree_preserved": after["supported"] and set(saved_fields) == set(fields),
                  "canonical_values": True, "widget_values": True, "appearances": True,
                  "untouched_values": True, "field_flags_preserved": True,
                  "widget_geometry_preserved": True, "untouched_appearances": True,
                  "manual_signatures_preserved": True,
                  "pages_rendered": True}
        details = []
        for name, field in fields.items():
            other = saved_fields.get(name)
            if other is None:
                checks["canonical_values"] = False
                continue
            if field["flags"] != other["flags"]:
                checks["field_flags_preserved"] = False
            checks["widget_geometry_preserved"] &= field["widgets"] == other["widgets"]
            if name not in normalized:
                if field["raw_value"] != other["raw_value"]:
                    checks["untouched_values"] = False
                checks["untouched_appearances"] &= (
                    [_appearance_fingerprint(w) for w, _ in original_widgets[name]] ==
                    [_appearance_fingerprint(w) for w, _ in saved_widgets.get(name, [])])
                continue
            expected = normalized[name]
            logical_ok = (other["value"] == expected and name in canonical_fields
                          and _plain(canonical_fields[name].get("/V", "")) == encoded[name])
            checks["canonical_values"] &= logical_ok
            detail = {"id": name, "value": expected, "logical": logical_ok, "widgets": []}
            for ref, meta in saved_widgets[name]:
                effective = _plain(_inherit(ref, "/V", ""))
                expected_raw = encoded[name]
                widget_ok = effective == expected_raw
                checks["widget_values"] &= widget_ok
                appearance = _appearance_check(ref, expected, field)
                checks["appearances"] &= appearance["ok"]
                detail["widgets"].append({**meta, "value_matches": widget_ok, "appearance": appearance})
            details.append(detail)
        before_manual = {f["id"]: f for f in info["manual_fields"]}
        after_manual = {f["id"]: f for f in after["manual_fields"]}
        checks["manual_signatures_preserved"] = before_manual == after_manual
        for name in before_manual:
            checks["manual_signatures_preserved"] &= (
                [_appearance_fingerprint(w) for w, _ in original_widgets[name]] ==
                [_appearance_fingerprint(w) for w, _ in saved_widgets.get(name, [])])
        for page_index in range(len(saved.pages)):
            render_page(candidate_path, page_index, scale=1)
        verified = all(checks.values())
        missing = [f["id"] for f in after["fields"] if f["required"] and not f["value"]]
        warnings = list(after["warnings"])
        if missing:
            warnings.append(f"Required fields are still empty: {', '.join(missing)}.")
        if not verified:
            reasons = [w["appearance"].get("reason", "") for f in details for w in f["widgets"] if not w["appearance"]["ok"]]
            raise FormworkError("Output verification failed. " + " ".join(reasons or [k for k, v in checks.items() if not v]))
        # Exclusive creation avoids overwriting a file created after initial checks.
        published = False
        try:
            with open(candidate_path, "rb") as candidate, open(output, "xb") as destination:
                published = True
                while chunk := candidate.read(1024 * 1024):
                    destination.write(chunk)
                destination.flush()
                os.fsync(destination.fileno())
        except BaseException:
            if published:
                output.unlink(missing_ok=True)
            raise
        if _sha256(output) != _sha256(candidate_path):
            output.unlink(missing_ok=True)
            raise FormworkError("The published PDF differs from the verified candidate.")
        return {"verified": True, "complete": not missing and not after_manual,
                "manual_fields": after["manual_fields"], "checks": checks, "warnings": warnings,
                "fields": details, "output": str(output), "sha256": _sha256(output),
                "source_sha256": original_hash, "editable": True}
    finally:
        if candidate_path:
            Path(candidate_path).unlink(missing_ok=True)
