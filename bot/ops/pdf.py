"""Operações de manipulação e edição de arquivos PDF."""

import io
from pathlib import Path
import shutil
import subprocess
from typing import Any

from PIL import Image, ImageOps
import pypdf
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from bot.ops import OpError
from bot.ops.paginas import parse_pages, parse_ranges


def merge(inputs: list[Path], out: Path) -> Path:
    """Mescla múltiplos arquivos PDF em um único arquivo de saída."""
    if not inputs:
        raise OpError("Nenhum arquivo fornecido para mesclar.")

    writer = pypdf.PdfWriter()
    for item in inputs:
        inp_path = Path(item)
        if not inp_path.exists():
            raise OpError(f"Arquivo não encontrado: {inp_path}")
        try:
            writer.append(str(inp_path))
        except Exception as e:
            raise OpError(f"Erro ao ler PDF para mesclagem: {e}")

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    return out


def split(inp: Path, out_dir: Path, spec: str | None) -> list[Path]:
    """Divide um PDF em vários arquivos conforme especificação ou página por página."""
    inp = Path(inp)
    out_dir = Path(out_dir)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    try:
        reader = pypdf.PdfReader(str(inp))
        total = len(reader.pages)
    except Exception as e:
        raise OpError(f"Erro ao abrir PDF: {e}")

    if total == 0:
        raise OpError("O PDF não contém páginas.")

    if spec is None:
        groups = [[i] for i in range(total)]
    else:
        groups = parse_ranges(spec, total)

    out_dir.mkdir(parents=True, exist_ok=True)
    generated_files: list[Path] = []

    for idx, group in enumerate(groups, start=1):
        target_path = out_dir / f"parte_{idx:02d}.pdf"
        writer = pypdf.PdfWriter()
        for page_idx in group:
            writer.add_page(reader.pages[page_idx])
        with open(target_path, "wb") as f:
            writer.write(f)
        generated_files.append(target_path)

    return generated_files


def extract_pages(inp: Path, out: Path, spec: str) -> Path:
    """Extrai as páginas especificadas para um novo arquivo PDF."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    try:
        reader = pypdf.PdfReader(str(inp))
        total = len(reader.pages)
    except Exception as e:
        raise OpError(f"Erro ao abrir PDF: {e}")

    selected_pages = parse_pages(spec, total)
    if not selected_pages:
        raise OpError("Nenhuma página selecionada.")

    writer = pypdf.PdfWriter()
    for page_idx in selected_pages:
        writer.add_page(reader.pages[page_idx])

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    return out


def remove_pages(inp: Path, out: Path, spec: str) -> Path:
    """Remove páginas especificadas de um arquivo PDF."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    try:
        reader = pypdf.PdfReader(str(inp))
        total = len(reader.pages)
    except Exception as e:
        raise OpError(f"Erro ao abrir PDF: {e}")

    to_remove = set(parse_pages(spec, total))
    remaining = [i for i in range(total) if i not in to_remove]
    if not remaining:
        raise OpError("Não é possível remover todas as páginas.")

    writer = pypdf.PdfWriter()
    for page_idx in remaining:
        writer.add_page(reader.pages[page_idx])

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    return out


def reorder(inp: Path, out: Path, spec: str) -> Path:
    """Reordena páginas de um arquivo PDF conforme sequência informada."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    try:
        reader = pypdf.PdfReader(str(inp))
        total = len(reader.pages)
    except Exception as e:
        raise OpError(f"Erro ao abrir PDF: {e}")

    ordered_pages = parse_pages(spec, total)
    if not ordered_pages:
        raise OpError("Nenhuma página selecionada.")

    writer = pypdf.PdfWriter()
    for page_idx in ordered_pages:
        writer.add_page(reader.pages[page_idx])

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    return out


def rotate(inp: Path, out: Path, degrees: int, spec: str | None = None) -> Path:
    """Gira páginas do PDF nos ângulos de 90, 180 ou 270 graus."""
    if degrees not in {90, 180, 270}:
        raise OpError("Ângulo de rotação inválido. Use 90, 180 ou 270.")

    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    try:
        reader = pypdf.PdfReader(str(inp))
        total = len(reader.pages)
    except Exception as e:
        raise OpError(f"Erro ao abrir PDF: {e}")

    targets = set(range(total)) if spec is None else set(parse_pages(spec, total))

    writer = pypdf.PdfWriter()
    for idx, page in enumerate(reader.pages):
        if idx in targets:
            page.rotate(degrees)
        writer.add_page(page)

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    return out


def protect(inp: Path, out: Path, password: str) -> Path:
    """Protege um arquivo PDF com senha utilizando criptografia AES-256."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")
    if not password:
        raise OpError("A senha não pode ser vazia.")

    try:
        reader = pypdf.PdfReader(str(inp))
        writer = pypdf.PdfWriter()
        writer.append(reader)
        writer.encrypt(user_password=password, algorithm="AES-256")

        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as f:
            writer.write(f)
        return out
    except Exception as e:
        raise OpError(f"Erro ao proteger PDF: {e}")


def unlock(inp: Path, out: Path, password: str) -> Path:
    """Remove a senha de um arquivo PDF protegido."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    try:
        reader = pypdf.PdfReader(str(inp))
    except Exception as e:
        raise OpError(f"Erro ao abrir PDF: {e}")

    if not reader.is_encrypted:
        raise OpError("Este PDF nao tem senha.")

    try:
        res = reader.decrypt(password)
    except Exception:
        res = 0

    if not res:
        raise OpError("Senha incorreta.")

    writer = pypdf.PdfWriter()
    writer.append(reader)

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    return out


def watermark_text(inp: Path, out: Path, text: str, opacity: float = 0.25) -> Path:
    """Adiciona marca d'água de texto diagonal centralizada em cada página."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    try:
        reader = pypdf.PdfReader(str(inp))
        writer = pypdf.PdfWriter()

        for page in reader.pages:
            w = float(page.mediabox.width)
            h = float(page.mediabox.height)
            rot = int(page.rotation or 0) % 360
            vis_w = h if rot in (90, 270) else w

            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(w, h))
            c.setFillColorRGB(0.5, 0.5, 0.5, alpha=opacity)
            c.translate(w / 2.0, h / 2.0)
            c.rotate((45 + rot) % 360)

            font_size = max(12.0, min(vis_w * 0.2, vis_w / (max(len(text), 6) * 0.7)))
            c.setFont("Helvetica-Bold", font_size)
            c.drawCentredString(0, -font_size / 3.0, text)
            c.showPage()
            c.save()

            buf.seek(0)
            wm_page = pypdf.PdfReader(buf).pages[0]
            page.merge_page(wm_page)
            writer.add_page(page)

        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as f:
            writer.write(f)
        return out
    except Exception as e:
        raise OpError(f"Erro ao adicionar marca d'água: {e}")


def page_numbers(
    inp: Path, out: Path, start: int = 1, position: str = "bottom-center"
) -> Path:
    """Adiciona numeração de páginas ao documento."""
    valid_positions = {"bottom-center", "bottom-right", "top-center", "top-right"}
    if position not in valid_positions:
        raise OpError(f"Posição inválida: {position}")

    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    try:
        reader = pypdf.PdfReader(str(inp))
        total = len(reader.pages)
        writer = pypdf.PdfWriter()
        margin = 10 * 72 / 25.4

        for idx, page in enumerate(reader.pages):
            n = start + idx
            num_str = f"{n} / {total}"
            w = float(page.mediabox.width)
            h = float(page.mediabox.height)
            rot = int(page.rotation or 0) % 360
            vis_w = h if rot in (90, 270) else w
            vis_h = w if rot in (90, 270) else h

            if position == "bottom-center":
                xv, yv, align = vis_w / 2.0, margin, "center"
            elif position == "bottom-right":
                xv, yv, align = vis_w - margin, margin, "right"
            elif position == "top-center":
                xv, yv, align = vis_w / 2.0, vis_h - margin - 10, "center"
            else:
                xv, yv, align = vis_w - margin, vis_h - margin - 10, "right"

            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(w, h))
            c.setFont("Helvetica", 10)

            if rot == 0:
                c.translate(xv, yv)
            elif rot == 90:
                c.translate(w - yv, xv)
                c.rotate(90)
            elif rot == 180:
                c.translate(w - xv, h - yv)
                c.rotate(180)
            elif rot == 270:
                c.translate(yv, h - xv)
                c.rotate(270)

            if align == "center":
                c.drawCentredString(0, 0, num_str)
            else:
                c.drawRightString(0, 0, num_str)

            c.showPage()
            c.save()

            buf.seek(0)
            wm_page = pypdf.PdfReader(buf).pages[0]
            page.merge_page(wm_page)
            writer.add_page(page)

        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as f:
            writer.write(f)
        return out
    except OpError:
        raise
    except Exception as e:
        raise OpError(f"Erro ao numerar páginas: {e}")


def crop_margins(inp: Path, out: Path, mm: float) -> Path:
    """Recorta as margens do PDF na quantidade de milímetros especificada."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    cut = mm * 72 / 25.4
    try:
        reader = pypdf.PdfReader(str(inp))
        writer = pypdf.PdfWriter()

        for page in reader.pages:
            new_left = float(page.mediabox.left) + cut
            new_bottom = float(page.mediabox.bottom) + cut
            new_right = float(page.mediabox.right) - cut
            new_top = float(page.mediabox.top) - cut

            if new_left >= new_right or new_bottom >= new_top:
                raise OpError("Margem de corte muito grande para a página.")

            page.mediabox.left = new_left
            page.mediabox.bottom = new_bottom
            page.mediabox.right = new_right
            page.mediabox.top = new_top
            page.cropbox.left = new_left
            page.cropbox.bottom = new_bottom
            page.cropbox.right = new_right
            page.cropbox.top = new_top
            writer.add_page(page)

        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as f:
            writer.write(f)
        return out
    except OpError:
        raise
    except Exception as e:
        raise OpError(f"Erro ao cortar margens: {e}")


def repair(inp: Path, out: Path) -> Path:
    """Repara um arquivo PDF corrompido ou com avisos de integridade."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    out.parent.mkdir(parents=True, exist_ok=True)
    qpdf_bin = shutil.which("qpdf")
    if qpdf_bin:
        try:
            res = subprocess.run(
                [qpdf_bin, str(inp), str(out)], capture_output=True, timeout=60
            )
            if res.returncode in (0, 3) and out.exists():
                return out
        except Exception:
            pass

    try:
        reader = pypdf.PdfReader(str(inp), strict=False)
        writer = pypdf.PdfWriter()
        writer.append(reader)
        with open(out, "wb") as f:
            writer.write(f)
        return out
    except Exception as e_pypdf:
        try:
            import pymupdf

            doc = pymupdf.open(str(inp))
            doc.save(str(out), garbage=4, deflate=True, clean=True)
            doc.close()
            return out
        except Exception:
            raise OpError(f"Não foi possível reparar o PDF: {e_pypdf}")


def images_to_pdf(images: list[Path], out: Path) -> Path:
    """Converte lista de imagens em páginas de PDF com formato A4."""
    if not images:
        raise OpError("Nenhuma imagem fornecida.")

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    margin = 10 * 72 / 25.4
    c = canvas.Canvas(str(out))

    try:
        for img_path in images:
            p = Path(img_path)
            if not p.exists():
                raise OpError(f"Imagem não encontrada: {p}")

            try:
                im = Image.open(p)
            except Exception as e:
                raise OpError(f"Erro ao abrir imagem: {e}")

            im = ImageOps.exif_transpose(im)

            if im.mode in ("RGBA", "LA") or (
                im.mode == "P" and "transparency" in im.info
            ):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[3])
                im = bg
            elif im.mode != "RGB":
                im = im.convert("RGB")

            img_w, img_h = im.size
            if img_w <= 0 or img_h <= 0:
                raise OpError("Dimensões inválidas da imagem.")

            if img_w > img_h:
                page_w, page_h = landscape(A4)
            else:
                page_w, page_h = A4

            c.setPageSize((page_w, page_h))
            avail_w = page_w - (2 * margin)
            avail_h = page_h - (2 * margin)

            scale = min(avail_w / img_w, avail_h / img_h)
            draw_w = img_w * scale
            draw_h = img_h * scale
            draw_x = (page_w - draw_w) / 2.0
            draw_y = (page_h - draw_h) / 2.0

            c.drawImage(ImageReader(im), draw_x, draw_y, width=draw_w, height=draw_h)
            c.showPage()

        c.save()
        return out
    except OpError:
        raise
    except Exception as e:
        raise OpError(f"Erro ao converter imagens para PDF: {e}")


def info(inp: Path) -> dict[str, Any]:
    """Retorna informações estruturadas sobre o arquivo PDF."""
    inp = Path(inp)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    try:
        reader = pypdf.PdfReader(str(inp))
        is_encrypted = bool(reader.is_encrypted)
        try:
            num_pages = len(reader.pages)
        except Exception:
            try:
                import pymupdf

                doc = pymupdf.open(str(inp))
                num_pages = doc.page_count
                doc.close()
            except Exception:
                num_pages = 0

        st_size = inp.stat().st_size
        tamanho_kb = max(1, round(st_size / 1024)) if st_size > 0 else 0
        return {
            "paginas": num_pages,
            "criptografado": is_encrypted,
            "tamanho_kb": tamanho_kb,
        }
    except Exception as e:
        raise OpError(f"Erro ao ler informações do PDF: {e}")
