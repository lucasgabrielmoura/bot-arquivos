"""Operações de conversão de e para arquivos PDF."""

import io
from pathlib import Path
import shutil
import subprocess
import tempfile

import pypdf

from bot.ops import OpError


def _run_cmd(args: list[str], timeout: int) -> subprocess.CompletedProcess:
    """Executa comando externo sem shell e trata timeouts e códigos de erro."""
    try:
        proc = subprocess.run(args, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise OpError("A conversao demorou demais.")

    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        last_chars = err[-200:] if err else f"código {proc.returncode}"
        raise OpError(f"Erro na execução da ferramenta: {last_chars}")

    return proc


def ferramentas() -> dict[str, bool]:
    """Retorna disponibilidade das ferramentas externas e bibliotecas opcionais."""
    has_gs = bool(shutil.which("gs") or shutil.which("gswin64c"))
    has_office = bool(shutil.which("soffice") or shutil.which("libreoffice"))
    has_ocrmypdf = bool(shutil.which("ocrmypdf"))
    has_qpdf = bool(shutil.which("qpdf"))

    try:
        import pymupdf  # noqa: F401

        has_pymupdf = True
    except ImportError:
        has_pymupdf = False

    try:
        import pdf2docx  # noqa: F401

        has_pdf2docx = True
    except ImportError:
        has_pdf2docx = False

    return {
        "ghostscript": has_gs,
        "libreoffice": has_office,
        "ocrmypdf": has_ocrmypdf,
        "qpdf": has_qpdf,
        "pymupdf": has_pymupdf,
        "pdf2docx": has_pdf2docx,
    }


def compress(inp: Path, out: Path, nivel: str = "recomendada") -> Path:
    """Comprime o PDF reduzindo o tamanho de fontes e imagens."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    nivel_map = {
        "baixa": "/printer",
        "recomendada": "/ebook",
        "extrema": "/screen",
    }
    if nivel not in nivel_map:
        raise OpError(f"Nível de compressão inválido: '{nivel}'. Use baixa, recomendada ou extrema.")

    out.parent.mkdir(parents=True, exist_ok=True)
    gs_bin = shutil.which("gs") or shutil.which("gswin64c")

    if gs_bin:
        args = [
            gs_bin,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.5",
            "-dNOPAUSE",
            "-dBATCH",
            "-dQUIET",
            f"-dPDFSETTINGS={nivel_map[nivel]}",
            f"-sOutputFile={str(out)}",
            str(inp),
        ]
        _run_cmd(args, timeout=300)
    else:
        try:
            import pymupdf
        except ImportError:
            raise OpError("Nenhuma ferramenta de compressão disponível (Ghostscript ou PyMuPDF).")

        try:
            doc = pymupdf.open(str(inp))
            doc.save(str(out), garbage=4, deflate=True, deflate_images=True, clean=True)
            doc.close()
        except Exception as e:
            raise OpError(f"Erro ao comprimir PDF: {e}")

    if out.exists() and inp.exists() and out.stat().st_size > inp.stat().st_size:
        shutil.copyfile(inp, out)

    return out


def pdf_to_images(
    inp: Path, out_dir: Path, fmt: str = "jpg", dpi: int = 150
) -> list[Path]:
    """Converte cada página de um PDF em um arquivo de imagem."""
    inp = Path(inp)
    out_dir = Path(out_dir)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    fmt_clean = fmt.lower().lstrip(".")
    if fmt_clean not in {"jpg", "jpeg", "png"}:
        raise OpError("Formato de imagem inválido. Use jpg ou png.")
    norm_fmt = "jpg" if fmt_clean in {"jpg", "jpeg"} else "png"

    try:
        import pymupdf
    except ImportError:
        raise OpError("PyMuPDF não está disponível.")

    try:
        doc = pymupdf.open(str(inp))
        out_dir.mkdir(parents=True, exist_ok=True)
        images: list[Path] = []

        for idx, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=dpi)
            img_path = out_dir / f"pagina_{idx:03d}.{norm_fmt}"
            pix.save(str(img_path))
            images.append(img_path)

        doc.close()
        return images
    except Exception as e:
        raise OpError(f"Erro ao converter PDF em imagens: {e}")


def office_to_pdf(inp: Path, out_dir: Path) -> Path:
    """Converte arquivo de suíte office para PDF usando LibreOffice headless."""
    valid_exts = {
        ".doc", ".docx", ".odt", ".rtf", ".txt",
        ".xls", ".xlsx", ".ods", ".csv",
        ".ppt", ".pptx", ".odp", ".html", ".htm",
    }
    inp = Path(inp)
    out_dir = Path(out_dir)

    if inp.suffix.lower() not in valid_exts:
        raise OpError(f"Formato não suportado para conversão: '{inp.suffix}'.")
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    cmd = shutil.which("soffice") or shutil.which("libreoffice")
    if not cmd:
        raise OpError("LibreOffice não está instalado.")

    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_profile = Path(tempfile.mkdtemp(prefix="soffice_profile_"))

    try:
        profile_uri = tmp_profile.as_uri()
        args = [
            cmd,
            "--headless",
            "--norestore",
            f"-env:UserInstallation={profile_uri}",
            "--convert-to", "pdf",
            "--outdir", str(out_dir),
            str(inp),
        ]
        _run_cmd(args, timeout=300)

        expected_pdf = out_dir / f"{inp.stem}.pdf"
        if not expected_pdf.exists():
            raise OpError("Arquivo PDF não foi gerado pelo LibreOffice.")
        return expected_pdf
    finally:
        shutil.rmtree(tmp_profile, ignore_errors=True)


def pdf_to_word(inp: Path, out: Path) -> Path:
    """Converte arquivo PDF em documento do Word (.docx)."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    try:
        from pdf2docx import Converter
    except ImportError:
        raise OpError("pdf2docx não está disponível.")

    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        cv = Converter(str(inp))
        cv.convert(str(out))
        cv.close()
        return out
    except Exception as e:
        raise OpError(f"Erro ao converter PDF para Word: {e}")


def pdf_to_excel(inp: Path, out: Path) -> Path:
    """Extrai tabelas de páginas do PDF em abas de uma planilha Excel."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    try:
        import openpyxl
        import pdfplumber
    except ImportError:
        raise OpError("pdfplumber ou openpyxl não estão disponíveis.")

    try:
        wb = openpyxl.Workbook()
        default_sheet = wb.active
        table_count = 0

        with pdfplumber.open(str(inp)) as pdf:
            for page in pdf.pages:
                pag_num = page.page_number
                tables = page.extract_tables() or []
                for n, table in enumerate(tables, start=1):
                    sheet_title = f"P{pag_num}_T{n}"
                    if table_count == 0:
                        ws = default_sheet
                        ws.title = sheet_title
                    else:
                        ws = wb.create_sheet(title=sheet_title)

                    for row in table:
                        ws.append(row)
                    table_count += 1

        if table_count == 0:
            raise OpError("Nenhuma tabela encontrada no PDF.")

        out.parent.mkdir(parents=True, exist_ok=True)
        wb.save(str(out))
        return out
    except OpError:
        raise
    except Exception as e:
        raise OpError(f"Erro ao converter PDF para Excel: {e}")


def pdf_to_pptx(inp: Path, out: Path) -> Path:
    """Converte páginas do PDF em slides de apresentação PowerPoint."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    try:
        import pptx
        from pptx.util import Pt
        import pymupdf
    except ImportError:
        raise OpError("pymupdf ou python-pptx não estão disponíveis.")

    try:
        doc = pymupdf.open(str(inp))
        if doc.page_count == 0:
            doc.close()
            raise OpError("O PDF não tem páginas.")

        prs = pptx.Presentation()
        first_page = doc[0]
        prs.slide_width = Pt(first_page.rect.width)
        prs.slide_height = Pt(first_page.rect.height)

        blank_layout = None
        for layout in prs.slide_layouts:
            if len(layout.placeholders) == 0:
                blank_layout = layout
                break
        if blank_layout is None:
            blank_layout = prs.slide_layouts[6]

        for page in doc:
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            slide = prs.slides.add_slide(blank_layout)
            slide.shapes.add_picture(
                io.BytesIO(img_bytes),
                0,
                0,
                width=prs.slide_width,
                height=prs.slide_height,
            )

        doc.close()
        out.parent.mkdir(parents=True, exist_ok=True)
        prs.save(str(out))
        return out
    except OpError:
        raise
    except Exception as e:
        raise OpError(f"Erro ao converter PDF para apresentação: {e}")


def pdf_to_text(inp: Path, out: Path) -> Path:
    """Extrai texto estruturado de páginas de um arquivo PDF."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    try:
        reader = pypdf.PdfReader(str(inp))
        sections = []
        for idx, page in enumerate(reader.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            sections.append(f"--- Pagina {idx} ---\n\n{page_text}")

        content = "\n\n".join(sections)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        return out
    except Exception as e:
        raise OpError(f"Erro ao extrair texto do PDF: {e}")


def ocr(inp: Path, out: Path, idioma: str = "por+eng") -> Path:
    """Aplica reconhecimento óptico de caracteres (OCR) no PDF."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    cmd = shutil.which("ocrmypdf")
    if not cmd:
        raise OpError("ocrmypdf não está instalado.")

    out.parent.mkdir(parents=True, exist_ok=True)
    args = [cmd, "--skip-text", "-l", idioma, str(inp), str(out)]
    _run_cmd(args, timeout=900)
    return out


def pdf_to_pdfa(inp: Path, out: Path) -> Path:
    """Converte arquivo PDF existente no formato arquivístico PDF/A."""
    inp = Path(inp)
    out = Path(out)
    if not inp.exists():
        raise OpError("Arquivo não encontrado.")

    gs_bin = shutil.which("gs") or shutil.which("gswin64c")
    if not gs_bin:
        raise OpError("Ghostscript não está instalado.")

    out.parent.mkdir(parents=True, exist_ok=True)
    args = [
        gs_bin,
        "-dPDFA=2",
        "-dPDFACompatibilityPolicy=1",
        "-sColorConversionStrategy=RGB",
        "-sDEVICE=pdfwrite",
        "-dNOPAUSE",
        "-dBATCH",
        "-dQUIET",
        f"-sOutputFile={str(out)}",
        str(inp),
    ]
    _run_cmd(args, timeout=300)
    return out
