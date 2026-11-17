"""Testes para o módulo de conversão bot/ops/converter.py."""

from pathlib import Path
import pptx
import pytest

from bot.ops import OpError
from bot.ops.converter import (
    compress,
    ferramentas,
    ocr,
    office_to_pdf,
    pdf_to_excel,
    pdf_to_images,
    pdf_to_pdfa,
    pdf_to_pptx,
    pdf_to_text,
    pdf_to_word,
)


def test_ferramentas():
    ferrs = ferramentas()
    required_keys = {
        "ghostscript",
        "libreoffice",
        "ocrmypdf",
        "qpdf",
        "pymupdf",
        "pdf2docx",
    }
    assert required_keys.issubset(ferrs.keys())
    for k, v in ferrs.items():
        assert isinstance(v, bool)


def test_compress_fallback_pymupdf(pdf5: Path, tmp_path: Path):
    out = tmp_path / "comprimido.pdf"
    compress(pdf5, out, nivel="recomendada")
    assert out.exists()
    assert out.stat().st_size > 0

    with pytest.raises(OpError):
        compress(pdf5, tmp_path / "fail.pdf", nivel="invalido")


def test_pdf_to_images(pdf5: Path, tmp_path: Path):
    out_dir_jpg = tmp_path / "imgs_jpg"
    imgs_jpg = pdf_to_images(pdf5, out_dir_jpg, fmt="jpg", dpi=100)
    assert len(imgs_jpg) == 5
    assert imgs_jpg[0].name == "pagina_001.jpg"

    out_dir_png = tmp_path / "imgs_png"
    imgs_png = pdf_to_images(pdf5, out_dir_png, fmt="png", dpi=100)
    assert len(imgs_png) == 5
    assert imgs_png[0].name == "pagina_001.png"

    with pytest.raises(OpError):
        pdf_to_images(pdf5, tmp_path / "imgs_fail", fmt="gif")


def test_pdf_to_text(pdf5: Path, tmp_path: Path):
    out = tmp_path / "extraido.txt"
    pdf_to_text(pdf5, out)
    assert out.exists()
    texto = out.read_text(encoding="utf-8")
    assert "--- Pagina 1 ---" in texto
    assert "Pagina 1" in texto
    assert "--- Pagina 5 ---" in texto
    assert "Pagina 5" in texto


def test_pdf_to_word(pdf5: Path, tmp_path: Path):
    out = tmp_path / "convertido.docx"
    pdf_to_word(pdf5, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_pdf_to_excel(pdf_table: Path, pdf5: Path, tmp_path: Path):
    out = tmp_path / "tabela.xlsx"
    pdf_to_excel(pdf_table, out)
    assert out.exists()
    assert out.stat().st_size > 0

    with pytest.raises(OpError, match="Nenhuma tabela encontrada no PDF."):
        pdf_to_excel(pdf5, tmp_path / "sem_tabela.xlsx")


def test_pdf_to_pptx(pdf5: Path, tmp_path: Path):
    out = tmp_path / "apresentacao.pptx"
    pdf_to_pptx(pdf5, out)
    assert out.exists()
    prs = pptx.Presentation(str(out))
    assert len(prs.slides) == 5


def test_office_to_pdf_skip(tmp_path: Path):
    if not ferramentas()["libreoffice"]:
        pytest.skip("LibreOffice ausente no sistema.")
    txt_file = tmp_path / "teste.txt"
    txt_file.write_text("Conteúdo de teste", encoding="utf-8")
    out_pdf = office_to_pdf(txt_file, tmp_path)
    assert out_pdf.exists()


def test_ocr_skip(pdf5: Path, tmp_path: Path):
    if not ferramentas()["ocrmypdf"]:
        pytest.skip("ocrmypdf ausente no sistema.")
    out_ocr = tmp_path / "ocr.pdf"
    ocr(pdf5, out_ocr)
    assert out_ocr.exists()


def test_pdf_to_pdfa_skip(pdf5: Path, tmp_path: Path):
    if not ferramentas()["ghostscript"]:
        pytest.skip("Ghostscript ausente no sistema.")
    out_pdfa = tmp_path / "pdfa.pdf"
    pdf_to_pdfa(pdf5, out_pdfa)
    assert out_pdfa.exists()
