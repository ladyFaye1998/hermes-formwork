"""Original synthetic PDFs for Formwork's tests; no third-party user data."""
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas


def make_form(path: str | Path) -> Path:
    path = Path(path)
    doc = canvas.Canvas(str(path), pagesize=(612, 792))
    doc.setTitle("Formwork original synthetic test form")
    doc.setFont("Helvetica-Bold", 18)
    doc.drawString(48, 740, "Workshop registration")
    doc.setFont("Helvetica", 10)
    doc.drawString(48, 714, "Original synthetic fixture. No real applicant or organization.")
    form = doc.acroForm
    doc.drawString(48, 671, "Full name")
    form.textfield(name="full_name", tooltip="Full name", x=48, y=638, width=300, height=24,
                   value="", maxlen=80, fontSize=11, fieldFlags="required",
                   borderColor=HexColor("#8a929f"), fillColor=HexColor("#ffffff"))
    doc.drawString(48, 605, "Workshop size")
    form.choice(name="size", tooltip="Workshop size", x=48, y=574, width=220, height=24,
                options=["small", "large"], value="small", fieldFlags="combo", fontSize=11)
    form.checkbox(name="agree", tooltip="Accept workshop terms", x=48, y=530, size=16,
                  checked=False, buttonStyle="check")
    doc.drawString(74, 534, "I accept the workshop terms")
    doc.showPage()
    doc.setFont("Helvetica-Bold", 18)
    doc.drawString(48, 740, "Organization details")
    doc.setFont("Helvetica", 10)
    doc.drawString(48, 689, "Company")
    form.textfield(name="company", tooltip="Company", x=48, y=654, width=300, height=24,
                   value="", maxlen=80, fontSize=11)
    doc.showPage()
    doc.save()
    return path


def make_source(path: str | Path, text: str = "Full name: Alex Rowan\nCompany: Northwind Studio\nWorkshop size: large") -> Path:
    path = Path(path)
    doc = canvas.Canvas(str(path), pagesize=(612, 792))
    doc.setTitle("Formwork original synthetic source")
    doc.setFont("Helvetica-Bold", 18)
    doc.drawString(48, 740, "Supporting facts")
    doc.setFont("Helvetica", 11)
    for index, line in enumerate(text.splitlines()):
        doc.drawString(48, 700 - index * 20, line)
    doc.showPage()
    doc.save()
    return path
