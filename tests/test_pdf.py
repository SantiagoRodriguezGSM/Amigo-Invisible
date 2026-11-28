from pypdf import PdfReader
from reportlab.pdfbase import pdfmetrics

from amigo_invisible.config import Settings
from amigo_invisible.pdf import SCRIPT, create_assignment_pdf, fit_name, register_fonts


def test_pdf_contains_accented_names(tmp_path):
    out = create_assignment_pdf("María José Núñez", "Íñigo Peña", tmp_path / "x.pdf", Settings())
    reader = PdfReader(out)
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    for expected in ("María José Núñez", "Íñigo Peña", "20 € – 30 €", "Nochebuena"):
        assert expected in text


def test_pdf_uses_custom_settings(tmp_path):
    settings = Settings(budget="15 €", event_date="Día de Reyes", event_year=2030)
    out = create_assignment_pdf("A", "B", tmp_path / "x.pdf", settings)
    text = PdfReader(out).pages[0].extract_text()
    assert "15 €" in text and "Día de Reyes" in text and "2030" in text


def test_creates_missing_output_directory(tmp_path):
    out = create_assignment_pdf("A", "B", tmp_path / "sub" / "dir" / "x.pdf", Settings())
    assert out.is_file()


def test_long_names_fit_in_the_card():
    register_fonts()
    max_width = 400
    name = "Ana Belén Fernández de la Vega y Ortiz de Zárate"
    lines, size = fit_name(name, SCRIPT, 58, max_width)
    assert len(lines) == 2
    assert all(pdfmetrics.stringWidth(line, SCRIPT, size) <= max_width for line in lines)


def test_short_name_is_single_line_at_max_size():
    register_fonts()
    assert fit_name("Ana", SCRIPT, 58, 400) == (["Ana"], 58)
