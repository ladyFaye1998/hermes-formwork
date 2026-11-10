from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject, TextStringObject

from formwork.engine import FormworkError, extract_text, fill_pdf, inspect_pdf, render_page
from pdf_fixtures import make_form, make_source


def rewrite(source, output, mutate):
    writer = PdfWriter()
    writer.clone_document_from_reader(PdfReader(source))
    mutate(writer)
    writer.write(output)
    return output


def test_inspection_maps_canonical_fields_and_all_pages(tmp_path):
    source = make_form(tmp_path / "form.pdf")
    info = inspect_pdf(source)
    assert info["supported"], info
    assert info["page_count"] == 2
    fields = {f["id"]: f for f in info["fields"]}
    assert set(fields) == {"full_name", "size", "agree", "company"}
    assert fields["full_name"]["required"] is True
    assert fields["agree"]["value"] is False
    assert fields["size"]["options"] == [{"value": "small", "label": "small"}, {"value": "large", "label": "large"}]
    assert fields["company"]["page"] == 1
    assert fields["full_name"]["display_rect"] == [48, 130, 348, 154]


def test_real_editable_roundtrip_and_saved_appearances(tmp_path):
    source = make_form(tmp_path / "original.pdf")
    original_bytes = source.read_bytes()
    output = tmp_path / "completed.pdf"
    values = {"full_name": "Alex Rowan", "size": "large", "agree": True, "company": "Northwind Studio"}
    result = fill_pdf(source, output, values)
    assert result["verified"] and result["complete"]
    assert all(result["checks"].values())
    assert source.read_bytes() == original_bytes
    stored = PdfReader(output).get_fields()
    assert stored["full_name"]["/V"] == "Alex Rowan"
    assert stored["size"]["/V"] == "large"
    assert str(stored["agree"]["/V"]) == "/Yes"
    assert stored["company"]["/V"] == "Northwind Studio"
    assert "/AcroForm" in PdfReader(output).trailer["/Root"]
    assert render_page(output, 0).startswith(b"\x89PNG")
    for field in result["fields"]:
        assert all(w["appearance"]["ok"] for w in field["widgets"])


def test_checkboxes_can_be_unchecked_and_untouched_values_survive(tmp_path):
    source = make_form(tmp_path / "original.pdf")
    one = tmp_path / "one.pdf"
    two = tmp_path / "two.pdf"
    fill_pdf(source, one, {"full_name": "Alex Rowan", "agree": True})
    result = fill_pdf(one, two, {"agree": False})
    assert result["verified"]
    assert PdfReader(two).get_fields()["full_name"]["/V"] == "Alex Rowan"
    assert str(PdfReader(two).get_fields()["agree"]["/V"]) == "/Off"


def test_source_text_is_page_numbered_and_verbatim(tmp_path):
    source = make_source(tmp_path / "facts.pdf")
    pages = extract_text(source)
    assert len(pages) == 1 and pages[0]["page"] == 0
    assert "Full name: Alex Rowan" in pages[0]["text"]


@pytest.mark.parametrize("values,message", [
    ({"unknown": "x"}, "Unknown field"),
    ({"full_name": "x" * 81}, "maximum length"),
    ({"full_name": "Ren\u00e9"}, "unsupported characters"),
    ({"agree": "true"}, "true or false"),
    ({"size": "giant"}, "declared option"),
    ({"full_name": "two\nlines"}, "single-line"),
])
def test_invalid_values_never_publish_output(tmp_path, values, message):
    source = make_form(tmp_path / "form.pdf")
    output = tmp_path / "out.pdf"
    with pytest.raises(FormworkError, match=message):
        fill_pdf(source, output, values)
    assert not output.exists()


def test_original_and_existing_output_cannot_be_replaced(tmp_path):
    source = make_form(tmp_path / "form.pdf")
    before = source.read_bytes()
    with pytest.raises(FormworkError, match="never overwritten"):
        fill_pdf(source, source, {"full_name": "Alex"})
    output = tmp_path / "out.pdf"
    output.write_bytes(b"keep me")
    with pytest.raises(FormworkError, match="never overwritten"):
        fill_pdf(source, output, {"full_name": "Alex"})
    assert output.read_bytes() == b"keep me" and source.read_bytes() == before


def test_appearance_overflow_is_a_failure_not_verified(tmp_path):
    source = make_form(tmp_path / "form.pdf")
    output = tmp_path / "out.pdf"
    with pytest.raises(FormworkError, match="verification failed"):
        fill_pdf(source, output, {"full_name": "W" * 79})
    assert not output.exists()


def test_orphan_with_same_name_is_refused_not_reattached(tmp_path):
    original = make_form(tmp_path / "base.pdf")

    def corrupt(writer):
        acro = writer.root_object["/AcroForm"]
        field = acro["/Fields"][0].get_object()
        duplicate = DictionaryObject({NameObject("/T"): TextStringObject(str(field["/T"])),
                                      NameObject("/FT"): NameObject("/Tx")})
        acro["/Fields"][0] = writer._add_object(duplicate)

    source = rewrite(original, tmp_path / "ambiguous.pdf", corrupt)
    info = inspect_pdf(source)
    assert not info["supported"]
    assert any("Ambiguous" in reason for reason in info["rejections"])
    with pytest.raises(FormworkError):
        fill_pdf(source, tmp_path / "out.pdf", {"full_name": "Alex"})


@pytest.mark.parametrize("kind", ["signed", "xfa", "encrypted", "radio"])
def test_unsupported_forms_refuse_safely(tmp_path, kind):
    original = make_form(tmp_path / "base.pdf")

    def mutate(writer):
        field = writer.root_object["/AcroForm"]["/Fields"][0].get_object()
        if kind == "signed":
            field[NameObject("/FT")] = NameObject("/Sig")
            field[NameObject("/V")] = DictionaryObject({NameObject("/Type"): NameObject("/Sig")})
        elif kind == "xfa":
            writer.root_object["/AcroForm"][NameObject("/XFA")] = TextStringObject("unsupported")
        elif kind == "encrypted":
            # ReportLab writes text-valued IDs; let pypdf create byte IDs for
            # this independently generated encrypted negative-control fixture.
            writer._ID = None
            writer.encrypt("secret")
        else:
            field[NameObject("/FT")] = NameObject("/Btn")
            field[NameObject("/Ff")] = NumberObject(32768)

    source = rewrite(original, tmp_path / f"{kind}.pdf", mutate)
    assert not inspect_pdf(source)["supported"]
    with pytest.raises(FormworkError):
        fill_pdf(source, tmp_path / "out.pdf", {"full_name": "Alex"})


def test_empty_signature_is_preserved_as_manual_work(tmp_path):
    original = make_form(tmp_path / "base.pdf")

    def empty_signature(writer):
        field = writer.root_object["/AcroForm"]["/Fields"][0].get_object()
        field[NameObject("/FT")] = NameObject("/Sig")
        field.pop(NameObject("/V"), None)
        field[NameObject("/TU")] = TextStringObject("Applicant signature")

    source = rewrite(original, tmp_path / "unsigned.pdf", empty_signature)
    info = inspect_pdf(source)
    assert info["supported"], info
    assert "full_name" not in {f["id"] for f in info["fields"]}
    assert info["manual_fields"][0]["id"] == "full_name"
    output = tmp_path / "out.pdf"
    result = fill_pdf(source, output, {"company": "Northwind Studio", "agree": True})
    assert result["verified"] and not result["complete"]
    assert result["checks"]["manual_signatures_preserved"]
    assert any("Manual signature still needed" in warning for warning in result["warnings"])
    signature = PdfReader(output).get_fields()["full_name"]
    assert signature["/FT"] == "/Sig" and not signature.get("/V")


def test_hierarchical_field_name_matches_canonical_tree(tmp_path):
    original = make_form(tmp_path / "base.pdf")

    def nested(writer):
        acro = writer.root_object["/AcroForm"]
        child_ref = acro["/Fields"][0]
        parent = DictionaryObject({NameObject("/T"): TextStringObject("applicant"),
                                   NameObject("/Kids"): ArrayObject([child_ref])})
        parent_ref = writer._add_object(parent)
        child_ref.get_object()[NameObject("/Parent")] = parent_ref
        acro["/Fields"][0] = parent_ref

    source = rewrite(original, tmp_path / "nested.pdf", nested)
    assert inspect_pdf(source)["supported"]
    result = fill_pdf(source, tmp_path / "filled.pdf", {"applicant.full_name": "Alex Rowan"})
    assert result["verified"]
    assert PdfReader(tmp_path / "filled.pdf").get_fields()["applicant.full_name"]["/V"] == "Alex Rowan"


def test_rotated_page_coordinates_and_fill(tmp_path):
    original = make_form(tmp_path / "base.pdf")
    source = rewrite(original, tmp_path / "rotated.pdf", lambda w: w.pages[0].rotate(90))
    info = inspect_pdf(source)
    assert info["supported"]
    field = next(f for f in info["fields"] if f["id"] == "full_name")
    assert info["pages"][0]["width"] == 792
    assert info["pages"][0]["height"] == 612
    assert field["display_rect"] == [638, 48, 662, 348]
    result = fill_pdf(source, tmp_path / "out.pdf", {"full_name": "Alex Rowan"})
    assert result["verified"]


def test_choice_export_value_and_visible_label_can_differ(tmp_path):
    original = make_form(tmp_path / "base.pdf")

    def options(writer):
        field = writer.root_object["/AcroForm"]["/Fields"][1].get_object()
        field[NameObject("/Opt")] = ArrayObject([
            ArrayObject([TextStringObject("sm"), TextStringObject("Small group")]),
            ArrayObject([TextStringObject("lg"), TextStringObject("Large group")]),
        ])
        field[NameObject("/V")] = TextStringObject("sm")

    source = rewrite(original, tmp_path / "options.pdf", options)
    result = fill_pdf(source, tmp_path / "out.pdf", {"size": "lg"})
    assert result["verified"]
    assert PdfReader(tmp_path / "out.pdf").get_fields()["size"]["/V"] == "lg"
    assert result["fields"][0]["widgets"][0]["appearance"]["visible_text"].strip() == "Large group"


def test_repeated_field_widgets_on_separate_pages_update_together(tmp_path):
    original = make_form(tmp_path / "base.pdf")

    def repeat(writer):
        acro = writer.root_object["/AcroForm"]
        first_ref, second_ref = acro["/Fields"][0], acro["/Fields"][3]
        parent = DictionaryObject({NameObject("/T"): TextStringObject("shared_name"),
                                   NameObject("/FT"): NameObject("/Tx"),
                                   NameObject("/V"): TextStringObject(""),
                                   NameObject("/Kids"): ArrayObject([first_ref, second_ref])})
        parent_ref = writer._add_object(parent)
        for child_ref in (first_ref, second_ref):
            child = child_ref.get_object()
            child[NameObject("/Parent")] = parent_ref
            for key in ("/T", "/FT", "/V"):
                child.pop(NameObject(key), None)
        acro[NameObject("/Fields")] = ArrayObject([parent_ref, acro["/Fields"][1], acro["/Fields"][2]])

    source = rewrite(original, tmp_path / "repeated.pdf", repeat)
    info = inspect_pdf(source)
    assert info["supported"], info
    field = next(f for f in info["fields"] if f["id"] == "shared_name")
    assert len(field["widgets"]) == 2
    result = fill_pdf(source, tmp_path / "out.pdf", {"shared_name": "Alex Rowan"})
    assert result["verified"]
    assert len(result["fields"][0]["widgets"]) == 2
