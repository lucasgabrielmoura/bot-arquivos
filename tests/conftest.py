"""Fixtures compartilhadas para testes automatizados com pytest."""

from pathlib import Path
from PIL import Image
import pytest
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle


@pytest.fixture
def pdf5(tmp_path: Path) -> Path:
    """Gera um PDF de 5 páginas contendo 'Pagina N' em cada uma."""
    pdf_path = tmp_path / "pdf5.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    for i in range(1, 6):
        c.drawString(100, 700, f"Pagina {i}")
        c.showPage()
    c.save()
    return pdf_path


@pytest.fixture
def pdf1(tmp_path: Path) -> Path:
    """Gera um PDF de 1 página com texto 'Pagina 1'."""
    pdf_path = tmp_path / "pdf1.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(100, 700, "Pagina 1")
    c.showPage()
    c.save()
    return pdf_path


@pytest.fixture
def pdf_table(tmp_path: Path) -> Path:
    """Gera um PDF com uma tabela desenhada via ReportLab Table."""
    pdf_path = tmp_path / "tabela.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    dados = [
        ["Item", "Quantidade", "Preço"],
        ["Caneta", "10", "2.50"],
        ["Caderno", "5", "15.00"],
    ]
    t = Table(dados)
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ]
        )
    )
    doc.build([t])
    return pdf_path


@pytest.fixture
def img_png_rgba(tmp_path: Path) -> Path:
    """Gera uma imagem PNG com canal alfa (RGBA)."""
    img_path = tmp_path / "imagem_rgba.png"
    im = Image.new("RGBA", (150, 100), (255, 0, 0, 128))
    im.save(str(img_path))
    return img_path


@pytest.fixture
def img_jpg(tmp_path: Path) -> Path:
    """Gera uma imagem JPG em modo RGB."""
    img_path = tmp_path / "imagem.jpg"
    im = Image.new("RGB", (100, 150), (0, 128, 255))
    im.save(str(img_path), format="JPEG")
    return img_path
