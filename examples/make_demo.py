"""Create Formwork's original, clearly synthetic demonstration packet.

Development-only: requires reportlab. From the repository root run
``.venv/Scripts/python examples/make_demo.py``. The eight PDFs contain invented
facts and .example addresses. Dietary requirements are intentionally absent
from the supporting sources, and occur in two forms for answer-once review.
No extraction result or filled output is manufactured by this script.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from reportlab.lib import colors
from reportlab.pdfgen import canvas


INK = colors.HexColor("#182c3a")
ACCENT = colors.HexColor("#336e69")
LINE = colors.HexColor("#abbebd")


def header(doc, title, subtitle):
    doc.setFillColor(ACCENT)
    doc.rect(0, 762, 612, 30, fill=True, stroke=False)
    doc.setFillColor(INK)
    doc.setFont("Helvetica-Bold", 23)
    doc.drawString(48, 716, title)
    doc.setFont("Helvetica", 10)
    doc.drawString(48, 692, subtitle)
    doc.setStrokeColor(LINE)
    doc.line(48, 674, 564, 674)
    doc.setFont("Helvetica", 8)
    doc.setFillColor(colors.HexColor("#60727a"))
    doc.drawString(48, 30, "FORMWORK DEMO  |  Original synthetic document. All people and organizations are fictional.")
    doc.setFillColor(INK)


def form_pdf(path: Path, title: str, rows: list[tuple], subtitle="Please complete the fields below."):
    doc = canvas.Canvas(str(path), pagesize=(612, 792))
    doc.setTitle(title + " - synthetic Formwork demo")
    header(doc, title, subtitle)
    y = 630
    for name, label, kind, *extra in rows:
        doc.setFillColor(INK)
        doc.setFont("Helvetica-Bold", 10)
        doc.drawString(48, y, label)
        if kind == "checkbox":
            doc.acroForm.checkbox(name=name, tooltip=label, x=48, y=y - 31,
                                 size=17, checked=False, buttonStyle="check",
                                 fieldFlags="",
                                 borderColor=LINE, fillColor=colors.white)
            doc.setFont("Helvetica", 9)
            doc.drawString(75, y - 27, "Select only if you agree.")
            y -= 67
        elif kind == "choice":
            options = extra[0]
            doc.acroForm.choice(name=name, tooltip=label, x=48, y=y - 34,
                                width=300, height=25, options=options,
                                value=options[0], fieldFlags="combo", fontSize=10,
                                borderColor=LINE, fillColor=colors.white)
            y -= 67
        elif kind == "multiline":
            doc.acroForm.textfield(name=name, tooltip=label, x=48, y=y - 68,
                                   width=516, height=58, maxlen=240, fontSize=10,
                                   fieldFlags="multiline", borderColor=LINE,
                                   fillColor=colors.white)
            y -= 99
        else:
            doc.acroForm.textfield(name=name, tooltip=label, x=48, y=y - 34,
                                   width=516, height=25, maxlen=110, fontSize=10,
                                   fieldFlags="", borderColor=LINE, fillColor=colors.white)
            y -= 67
    doc.showPage()
    doc.save()


def source_pdf(path: Path, title: str, facts: list[tuple[str, str]]):
    doc = canvas.Canvas(str(path), pagesize=(612, 792))
    doc.setTitle(title + " - synthetic Formwork demo")
    header(doc, title, "Supporting document - source facts for the demonstration packet.")
    y = 630
    for label, value in facts:
        doc.setFont("Helvetica-Bold", 10)
        doc.drawString(48, y, label)
        y -= 20
        doc.setFont("Helvetica", 11)
        # Deliberately short, exact source lines; no invisible overflow.
        for line in value.split("\n"):
            doc.drawString(48, y, line)
            y -= 17
        y -= 24
    doc.showPage()
    doc.save()


def make_demo(output: str | Path = "examples/demo") -> list[Path]:
    output = Path(output)
    forms, sources = output / "forms", output / "sources"
    forms.mkdir(parents=True, exist_ok=True)
    sources.mkdir(parents=True, exist_ok=True)
    planned = [forms / f"{name}.pdf" for name in ("supplier-onboarding", "speaker-profile", "workshop-registration", "venue-access")]
    planned += [sources / f"{name}.pdf" for name in ("company-profile", "presenter-bio", "event-brief", "contact-card")]
    existing = [path for path in planned if path.exists()]
    if existing:
        raise FileExistsError("Demo originals already exist; choose a new --output folder.")
    form_pdf(planned[0], "Supplier onboarding", [
        ("company_name", "Company name", "text"),
        ("company_number", "Company registration number", "text"),
        ("contact_name", "Contact full name", "text"),
        ("contact_email", "Contact email", "text"),
        ("registered_address", "Registered office address", "text"),
        ("service_category", "Service category", "choice", ["Design", "Consulting"]),
    ])
    form_pdf(planned[1], "Speaker profile", [
        ("full_name", "Full name", "text"),
        ("email", "Email", "text"),
        ("company_name", "Company name", "text"),
        ("job_title", "Job title", "text"),
        ("session_title", "Session title", "text"),
        ("bio", "Short biography", "multiline"),
    ])
    form_pdf(planned[2], "Workshop registration", [
        ("full_name", "Full name", "text"),
        ("email", "Email", "text"),
        ("company_name", "Company name", "text"),
        ("workshop_size", "Workshop size", "choice", ["small", "large"]),
        ("dietary_requirements", "Dietary requirements", "text"),
        ("photo_consent", "Consent to event photographs", "checkbox"),
    ], "Dietary information and consent must come from the participant.")
    form_pdf(planned[3], "Venue access", [
        ("full_name", "Full name", "text"),
        ("email", "Email", "text"),
        ("company_name", "Company name", "text"),
        ("visit_date", "Visit date", "text"),
        ("dietary_requirements", "Dietary requirements", "text"),
    ])
    source_pdf(planned[4], "Company profile", [
        ("Company name", "Northstar Studio Ltd"),
        ("Company registration number", "07845912"),
        ("Registered office address", "18 Riverside Lane, Bristol, BS1 4NA"),
        ("Service category", "Design"),
        ("Company contact", "Alex Rowan - alex@northstar.example"),
    ])
    source_pdf(planned[5], "Presenter biography", [
        ("Full name", "Alex Rowan"),
        ("Company name", "Northstar Studio Ltd"),
        ("Job title", "Creative Director"),
        ("Short biography", "Alex Rowan leads Northstar Studio's design practice.\nAlex helps small teams turn research into useful products."),
    ])
    source_pdf(planned[6], "Event brief", [
        ("Event", "Fieldnotes - a workshop on practical design"),
        ("Participant", "Alex Rowan"),
        ("Session title", "Designing with Evidence"),
        ("Workshop size", "large"),
        ("Visit date", "20 November 2026"),
        ("Note", "Dietary preferences have not been collected.\nPhotograph consent must be confirmed by the participant."),
    ])
    source_pdf(planned[7], "Contact card", [
        ("Full name", "Alex Rowan"),
        ("Email", "alex@northstar.example"),
        ("Company name", "Northstar Studio Ltd"),
        ("Job title", "Creative Director"),
    ])
    return planned


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="examples/demo")
    args = parser.parse_args()
    for path in make_demo(args.output):
        print(path)
