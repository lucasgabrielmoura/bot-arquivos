"""Testes para operações com PDF em bot/ops/pdf.py."""

from pathlib import Path
import pypdf
import pytest

from bot.ops import OpError
from bot.ops.pdf import (
    crop_margins,
    extract_pages,
    images_to_pdf,
    info,
    merge,
    page_numbers,
    protect,
    remove_pages,
    reorder,
    repair,
    rotate,
    split,
    unlock,
    watermark_text,
)


def test_merge(pdf5: Path, pdf1: Path, tmp_path: Path):
    out = tmp_path / "merged.pdf"
    merge([pdf5, pdf1], out)
    reader = pypdf.PdfReader(str(out))
    assert len(reader.pages) == 6

    with pytest.raises(OpError):
        merge([], tmp_path / "empty.pdf")


def test_split(pdf5: Path, tmp_path: Path):
    out_dir_all = tmp_path / "split_all"
    parts_all = split(pdf5, out_dir_all, None)
    assert len(parts_all) == 5
    assert parts_all[0].name == "parte_01.pdf"
    assert parts_all[4].name == "parte_05.pdf"

    out_dir_spec = tmp_path / "split_spec"
    parts_spec = split(pdf5, out_dir_spec, "1-2, 3-5")
    assert len(parts_spec) == 2
    r1 = pypdf.PdfReader(str(parts_spec[0]))
    r2 = pypdf.PdfReader(str(parts_spec[1]))
    assert len(r1.pages) == 2
    assert len(r2.pages) == 3


def test_extract_pages(pdf5: Path, tmp_path: Path):
    out = tmp_path / "extracted.pdf"
    extract_pages(pdf5, out, "2, 4")
    reader = pypdf.PdfReader(str(out))
    assert len(reader.pages) == 2
    assert "Pagina 2" in reader.pages[0].extract_text()
    assert "Pagina 4" in reader.pages[1].extract_text()


def test_remove_pages(pdf5: Path, tmp_path: Path):
    out = tmp_path / "removed.pdf"
    remove_pages(pdf5, out, "1, 3, 5")
    reader = pypdf.PdfReader(str(out))
    assert len(reader.pages) == 2
    assert "Pagina 2" in reader.pages[0].extract_text()
    assert "Pagina 4" in reader.pages[1].extract_text()

    with pytest.raises(OpError):
        remove_pages(pdf5, tmp_path / "fail.pdf", "1-5")


def test_reorder(pdf5: Path, tmp_path: Path):
    out = tmp_path / "reordered.pdf"
    reorder(pdf5, out, "3, 1, 2")
    reader = pypdf.PdfReader(str(out))
    assert len(reader.pages) == 3
    assert "Pagina 3" in reader.pages[0].extract_text()
    assert "Pagina 1" in reader.pages[1].extract_text()
    assert "Pagina 2" in reader.pages[2].extract_text()


def test_rotate(pdf5: Path, tmp_path: Path):
    out = tmp_path / "rotated.pdf"
    rotate(pdf5, out, 90, "1")
    reader = pypdf.PdfReader(str(out))
    assert reader.pages[0].rotation == 90
    assert reader.pages[1].rotation == 0

    with pytest.raises(OpError):
        rotate(pdf5, tmp_path / "invalid_rot.pdf", 45)

    out_all = tmp_path / "rotated_all.pdf"
    rotate(pdf5, out_all, 180, None)
    reader_all = pypdf.PdfReader(str(out_all))
    for page in reader_all.pages:
        assert page.rotation == 180


def test_protect_and_unlock(pdf5: Path, tmp_path: Path):
    prot_out = tmp_path / "protected.pdf"
    protect(pdf5, prot_out, "senha123")
    r_prot = pypdf.PdfReader(str(prot_out))
    assert r_prot.is_encrypted is True

    with pytest.raises(OpError, match="Senha incorreta."):
        unlock(prot_out, tmp_path / "unlocked_fail.pdf", "senha_errada")

    unl_out = tmp_path / "unlocked.pdf"
    unlock(prot_out, unl_out, "senha123")
    r_unl = pypdf.PdfReader(str(unl_out))
    assert r_unl.is_encrypted is False
    assert len(r_unl.pages) == 5

    with pytest.raises(OpError, match="Este PDF nao tem senha."):
        unlock(pdf5, tmp_path / "already_unlocked.pdf", "qualquer")


def test_watermark(pdf5: Path, tmp_path: Path):
    out = tmp_path / "watermarked.pdf"
    watermark_text(pdf5, out, "CONFIDENCIAL")
    reader = pypdf.PdfReader(str(out))
    assert len(reader.pages) == 5
    assert "CONFIDENCIAL" in reader.pages[0].extract_text()


def test_page_numbers(pdf5: Path, tmp_path: Path):
    out = tmp_path / "numbered.pdf"
    page_numbers(pdf5, out, start=1, position="bottom-center")
    reader = pypdf.PdfReader(str(out))
    assert len(reader.pages) == 5
    text_p1 = reader.pages[0].extract_text()
    assert "1 / 5" in text_p1


def test_crop_margins(pdf5: Path, tmp_path: Path):
    out = tmp_path / "cropped.pdf"
    crop_margins(pdf5, out, mm=5.0)
    r_orig = pypdf.PdfReader(str(pdf5))
    r_crop = pypdf.PdfReader(str(out))
    assert float(r_crop.pages[0].mediabox.width) < float(r_orig.pages[0].mediabox.width)

    with pytest.raises(OpError):
        crop_margins(pdf5, tmp_path / "too_large.pdf", mm=2000.0)


def test_repair(pdf5: Path, tmp_path: Path):
    out = tmp_path / "repaired.pdf"
    repair(pdf5, out)
    reader = pypdf.PdfReader(str(out))
    assert len(reader.pages) == 5


def test_images_to_pdf(img_png_rgba: Path, img_jpg: Path, tmp_path: Path):
    out = tmp_path / "from_images.pdf"
    images_to_pdf([img_png_rgba, img_jpg], out)
    reader = pypdf.PdfReader(str(out))
    assert len(reader.pages) == 2

    with pytest.raises(OpError):
        images_to_pdf([], tmp_path / "none.pdf")


def test_info(pdf5: Path, tmp_path: Path):
    dados = info(pdf5)
    assert dados["paginas"] == 5
    assert dados["criptografado"] is False
    assert isinstance(dados["tamanho_kb"], int)
    assert dados["tamanho_kb"] >= 0

    prot = tmp_path / "prot_info.pdf"
    protect(pdf5, prot, "1234")
    dados_prot = info(prot)
    assert dados_prot["criptografado"] is True
    assert dados_prot["paginas"] == 5
