from __future__ import annotations

import asyncio
import functools
import logging
import shutil
import time
import uuid
import zipfile
from pathlib import Path

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.config import Config, carregar
from bot.ops import OpError, converter, paginas, pdf

logger = logging.getLogger(__name__)

OFFICE_EXTENSIONS = {
    ".doc", ".docx", ".odt", ".rtf", ".txt",
    ".xls", ".xlsx", ".ods", ".csv",
    ".ppt", ".pptx", ".odp",
    ".html", ".htm",
}

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif",
}

global_semaphore: asyncio.Semaphore | None = None


def get_semaphore(max_jobs: int) -> asyncio.Semaphore:
    global global_semaphore
    if global_semaphore is None:
        global_semaphore = asyncio.Semaphore(max_jobs)
    return global_semaphore


def limpar_sessao(user_data: dict) -> None:
    sessao_dir = user_data.get("sessao_dir")
    if sessao_dir and isinstance(sessao_dir, Path):
        shutil.rmtree(sessao_dir, ignore_errors=True)
    user_data.clear()


def limpar_pasta_trabalho(pasta: Path) -> None:
    if pasta.exists():
        for item in pasta.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                try:
                    item.unlink()
                except OSError:
                    pass
    pasta.mkdir(parents=True, exist_ok=True)


def limpar_sessoes_antigas(user_dir: Path, sessao_atual_id: str) -> None:
    if not user_dir.exists():
        return
    agora = time.time()
    for item in user_dir.iterdir():
        if item.is_dir() and item.name != sessao_atual_id:
            try:
                if agora - item.stat().st_mtime > 3600:
                    shutil.rmtree(item, ignore_errors=True)
            except OSError:
                pass


def restrito(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return
        cfg: Config = context.bot_data["config"]
        if user.id not in cfg.usuarios:
            if update.callback_query:
                try:
                    await update.callback_query.answer("Acesso negado.", show_alert=True)
                except Exception:
                    pass
            if update.effective_message:
                await update.effective_message.reply_text(f"Acesso negado. Seu ID: {user.id}")
            return
        return await func(update, context, *args, **kwargs)

    return wrapper


def montar_menu(arquivos: list[Path]) -> tuple[str, InlineKeyboardMarkup]:
    n = len(arquivos)
    exts = [f.suffix.lower() for f in arquivos]

    all_pdf = all(e == ".pdf" for e in exts)
    all_images = all(e in IMAGE_EXTENSIONS for e in exts)
    all_office = all(e in OFFICE_EXTENSIONS for e in exts)

    botoes: list[InlineKeyboardButton] = []
    texto = f"📎 {n} arquivo(s) recebido(s). Envie mais ou escolha:"

    if all_pdf and n == 1:
        ops = [
            ("Comprimir", "op:compress"),
            ("Dividir", "op:split"),
            ("Extrair páginas", "op:extract"),
            ("Remover páginas", "op:remove"),
            ("Reordenar", "op:reorder"),
            ("Girar", "op:rotate"),
            ("Proteger", "op:protect"),
            ("Desbloquear", "op:unlock"),
            ("Marca d'água", "op:watermark"),
            ("Numerar páginas", "op:page_numbers"),
            ("Cortar margens", "op:crop_margins"),
            ("Reparar", "op:repair"),
            ("PDF→JPG", "op:pdf_to_jpg"),
            ("PDF→PNG", "op:pdf_to_png"),
            ("PDF→Word", "op:pdf_to_word"),
            ("PDF→Excel", "op:pdf_to_excel"),
            ("PDF→PowerPoint", "op:pdf_to_pptx"),
            ("PDF→Texto", "op:pdf_to_text"),
            ("OCR", "op:ocr"),
            ("PDF/A", "op:pdf_to_pdfa"),
            ("Info", "op:info"),
        ]
        botoes = [InlineKeyboardButton(rotulo, callback_data=cb) for rotulo, cb in ops]
    elif all_pdf and n >= 2:
        ops = [
            ("Juntar", "op:merge"),
            ("Comprimir", "op:compress"),
        ]
        botoes = [InlineKeyboardButton(rotulo, callback_data=cb) for rotulo, cb in ops]
    elif all_images:
        ops = [
            ("Imagens→PDF", "op:images_to_pdf"),
        ]
        botoes = [InlineKeyboardButton(rotulo, callback_data=cb) for rotulo, cb in ops]
    elif all_office:
        ops = [
            ("Converter para PDF", "op:office_to_pdf"),
        ]
        botoes = [InlineKeyboardButton(rotulo, callback_data=cb) for rotulo, cb in ops]
    else:
        texto = f"📎 {n} arquivo(s) recebido(s).\nFormatos misturados ou não suportados. Limpe para recomeçar."
        botoes = []

    linhas: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(botoes), 2):
        linhas.append(botoes[i:i+2])
    linhas.append([InlineKeyboardButton("🗑 Limpar", callback_data="op:limpar")])

    return texto, InlineKeyboardMarkup(linhas)


async def cmd_meuid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user and update.effective_message:
        await update.effective_message.reply_text(f"Seu ID: {user.id}")


@restrito
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "Olá! Sou o seu assistente de manipulação e conversão de arquivos e PDFs.\n\n"
        "Como usar:\n"
        "1. Envie um ou mais arquivos (PDFs, imagens ou documentos Office/HTML).\n"
        "2. Escolha a operação desejada no menu interativo.\n\n"
        "Comandos disponíveis:\n"
        "• /ferramentas - Status dos conversores externos instalados\n"
        "• /cancelar - Cancela o processo atual e limpa a sessão\n"
        "• /limpar - Remove todos os arquivos enviados da sessão\n"
        "• /meuid - Exibe o seu ID do Telegram\n"
        "• /ajuda - Exibe este guia de ajuda"
    )
    if update.effective_message:
        await update.effective_message.reply_text(msg)


@restrito
async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


@restrito
async def cmd_ferramentas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        ferrs = await asyncio.to_thread(converter.ferramentas)
    except Exception:
        logger.exception("Erro ao obter status das ferramentas")
        if update.effective_message:
            await update.effective_message.reply_text("❌ Erro ao verificar ferramentas.")
        return

    linhas = ["🔧 Status das ferramentas externas:"]
    for nome, disponivel in ferrs.items():
        status = "✅" if disponivel else "❌"
        linhas.append(f"{status} {nome}")

    if update.effective_message:
        await update.effective_message.reply_text("\n".join(linhas))


@restrito
async def cmd_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    limpar_sessao(context.user_data)
    if update.effective_message:
        await update.effective_message.reply_text("Operação cancelada e sessão limpa.")


@restrito
async def cmd_limpar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    limpar_sessao(context.user_data)
    if update.effective_message:
        await update.effective_message.reply_text("Arquivos e sessão limpos.")


@restrito
async def on_file_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if not msg or not user:
        return

    cfg: Config = context.bot_data["config"]

    user_dir = cfg.pasta_trabalho / str(user.id)
    if "sessao_id" not in context.user_data:
        sessao_id = uuid.uuid4().hex
        sessao_dir = user_dir / sessao_id
        sessao_dir.mkdir(parents=True, exist_ok=True)
        context.user_data["sessao_id"] = sessao_id
        context.user_data["sessao_dir"] = sessao_dir
        context.user_data["arquivos"] = []
    else:
        sessao_id = context.user_data["sessao_id"]
        sessao_dir = context.user_data["sessao_dir"]
        sessao_dir.mkdir(parents=True, exist_ok=True)

    limpar_sessoes_antigas(user_dir, sessao_id)

    if msg.photo:
        photo = msg.photo[-1]
        file_id = photo.file_id
        file_size = photo.file_size or 0
        ext = ".jpg"
    elif msg.document:
        doc = msg.document
        file_id = doc.file_id
        file_size = doc.file_size or 0
        orig_name = doc.file_name or ""
        ext = Path(orig_name).suffix.lower()
        if not ext:
            ext = ".bin"
    else:
        return

    if cfg.api_url is None and file_size > 20 * 1024 * 1024:
        await msg.reply_text(
            "❌ Arquivo excede o limite de download de 20MB do Telegram sem servidor Bot API local."
        )
        return

    arquivos: list[Path] = context.user_data.setdefault("arquivos", [])
    n = len(arquivos) + 1
    safe_name = f"arq_{n}{ext}"
    dest_path = sessao_dir / safe_name

    try:
        tg_file = await context.bot.get_file(file_id)
        await tg_file.download_to_drive(custom_path=dest_path)
    except Exception:
        logger.exception("Erro ao baixar arquivo do Telegram")
        await msg.reply_text("❌ Erro ao baixar o arquivo. Tente novamente.")
        return

    arquivos.append(dest_path)
    context.user_data["aguardando"] = None

    old_menu_id = context.user_data.get("menu_msg_id")
    if old_menu_id:
        try:
            await context.bot.delete_message(chat_id=msg.chat_id, message_id=old_menu_id)
        except Exception:
            pass
        context.user_data["menu_msg_id"] = None

    texto_menu, teclado = montar_menu(arquivos)
    menu_msg = await msg.reply_text(texto_menu, reply_markup=teclado)
    context.user_data["menu_msg_id"] = menu_msg.message_id


@restrito
async def on_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()

    data = query.data or ""
    if data == "op:limpar":
        limpar_sessao(context.user_data)
        try:
            await query.edit_message_text("🗑 Sessão e arquivos limpos.")
        except Exception:
            pass
        return

    arquivos: list[Path] = context.user_data.get("arquivos", [])
    if not arquivos:
        try:
            await query.edit_message_text("❌ Nenhum arquivo na sessão. Envie os arquivos novamente.")
        except Exception:
            pass
        return

    if data == "op:rotate":
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("90° ↻", callback_data="rot:90"),
                InlineKeyboardButton("180°", callback_data="rot:180"),
                InlineKeyboardButton("270° ↺", callback_data="rot:270"),
            ],
            [InlineKeyboardButton("🗑 Limpar", callback_data="op:limpar")],
        ])
        await query.edit_message_text("Selecione o ângulo de rotação:", reply_markup=kb)
        return

    if data.startswith("rot:"):
        graus = int(data.split(":")[1])
        await executar_operacao(update, context, codigo="rotate", param={"degrees": graus})
        return

    if data == "op:compress":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Recomendada", callback_data="cmp:recomendada")],
            [
                InlineKeyboardButton("Baixa", callback_data="cmp:baixa"),
                InlineKeyboardButton("Extrema", callback_data="cmp:extrema"),
            ],
            [InlineKeyboardButton("🗑 Limpar", callback_data="op:limpar")],
        ])
        await query.edit_message_text("Selecione o nível de compressão:", reply_markup=kb)
        return

    if data.startswith("cmp:"):
        nivel = data.split(":")[1]
        await executar_operacao(update, context, codigo="compress", param={"nivel": nivel})
        return

    if data == "op:split":
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Cada página", callback_data="split:all"),
                InlineKeyboardButton("Por intervalos", callback_data="split:ranges"),
            ],
            [InlineKeyboardButton("🗑 Limpar", callback_data="op:limpar")],
        ])
        await query.edit_message_text("Como deseja dividir o PDF?", reply_markup=kb)
        return

    if data == "split:all":
        await executar_operacao(update, context, codigo="split", param={"spec": None})
        return

    if data == "split:ranges":
        context.user_data["aguardando"] = "split"
        await query.edit_message_text("Envie os intervalos de páginas (ex: 1-3, 4-8):")
        return

    if data in ("op:extract", "op:remove", "op:reorder"):
        try:
            info_res = await asyncio.to_thread(pdf.info, arquivos[0])
            tot = info_res.get("paginas", 0)
        except Exception:
            tot = "?"

        if data == "op:extract":
            context.user_data["aguardando"] = "extract"
            await query.edit_message_text(
                f"📄 O PDF possui {tot} página(s).\n"
                "Envie as páginas que deseja extrair (ex: 1-3, 5):"
            )
        elif data == "op:remove":
            context.user_data["aguardando"] = "remove"
            await query.edit_message_text(
                f"📄 O PDF possui {tot} página(s).\n"
                "Envie as páginas que deseja remover (ex: 2, 4-6):"
            )
        elif data == "op:reorder":
            context.user_data["aguardando"] = "reorder"
            await query.edit_message_text(
                f"📄 O PDF possui {tot} página(s).\n"
                "Envie a nova ordem das páginas (ex: 3, 1, 2):"
            )
        return

    if data == "op:protect":
        context.user_data["aguardando"] = "protect"
        await query.edit_message_text("Envie a senha para proteger o PDF:")
        return

    if data == "op:unlock":
        context.user_data["aguardando"] = "unlock"
        await query.edit_message_text("Envie a senha para desbloquear o PDF:")
        return

    if data == "op:watermark":
        context.user_data["aguardando"] = "watermark"
        await query.edit_message_text("Envie o texto para a marca d'água:")
        return

    if data == "op:page_numbers":
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Inferior Central", callback_data="num:bottom-center"),
                InlineKeyboardButton("Inferior Direito", callback_data="num:bottom-right"),
            ],
            [
                InlineKeyboardButton("Superior Central", callback_data="num:top-center"),
                InlineKeyboardButton("Superior Direito", callback_data="num:top-right"),
            ],
            [InlineKeyboardButton("🗑 Limpar", callback_data="op:limpar")],
        ])
        await query.edit_message_text("Escolha a posição do número de página:", reply_markup=kb)
        return

    if data.startswith("num:"):
        pos = data.split(":")[1]
        await executar_operacao(update, context, codigo="page_numbers", param={"position": pos})
        return

    if data == "op:crop_margins":
        context.user_data["aguardando"] = "crop_margins"
        await query.edit_message_text("Envie o corte das margens em mm (1 a 50, ex: 10 ou 12,5):")
        return

    if data.startswith("op:"):
        op_code = data.split(":")[1]
        await executar_operacao(update, context, codigo=op_code)
        return


@restrito
async def on_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.text:
        return

    aguardando = context.user_data.get("aguardando")
    if not aguardando:
        await msg.reply_text("Envie um arquivo para começar ou use /ajuda.")
        return

    context.user_data["aguardando"] = None
    texto_usuario = msg.text.strip()

    if aguardando in ("protect", "unlock"):
        try:
            await msg.delete()
        except Exception:
            pass
        await executar_operacao(update, context, codigo=aguardando, param={"password": texto_usuario})
        return

    if aguardando in ("extract", "remove", "reorder", "split"):
        await executar_operacao(update, context, codigo=aguardando, param={"spec": texto_usuario})
        return

    if aguardando == "watermark":
        await executar_operacao(update, context, codigo="watermark", param={"text": texto_usuario})
        return

    if aguardando == "crop_margins":
        try:
            mm_val = float(texto_usuario.replace(",", "."))
            if not (1.0 <= mm_val <= 50.0):
                raise ValueError()
        except ValueError:
            await msg.reply_text("❌ Informe um número válido entre 1 e 50 mm.")
            limpar_sessao(context.user_data)
            return
        await executar_operacao(update, context, codigo="crop_margins", param={"mm": mm_val})
        return


async def executar_operacao(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    codigo: str,
    param: dict | None = None,
) -> None:
    if param is None:
        param = {}

    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    logger.info("user_id=%s op=%s", user.id, codigo)

    status_msg = await chat.send_message("⏳ Processando...")

    arquivos: list[Path] = context.user_data.get("arquivos", [])
    sessao_dir: Path | None = context.user_data.get("sessao_dir")

    if not arquivos or not sessao_dir or not sessao_dir.exists():
        try:
            await status_msg.edit_text("❌ Sessão expirada ou arquivos ausentes. Envie-os novamente.")
        except Exception:
            pass
        limpar_sessao(context.user_data)
        return

    cfg: Config = context.bot_data["config"]
    sem = get_semaphore(cfg.max_jobs)
    out_dir = sessao_dir / "saida"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        async with sem:
            if codigo == "info":
                res = await asyncio.to_thread(pdf.info, arquivos[0])
                pags = res.get("paginas", 0)
                cripto = "Sim" if res.get("criptografado") else "Não"
                tam_kb = res.get("tamanho_kb", 0)
                texto_info = (
                    f"📄 Informações do PDF:\n"
                    f"• Total de páginas: {pags}\n"
                    f"• Criptografado: {cripto}\n"
                    f"• Tamanho: {tam_kb} KB"
                )
                await chat.send_message(texto_info)
                try:
                    await status_msg.delete()
                except Exception:
                    pass
                limpar_sessao(context.user_data)
                return

            files_to_send: list[tuple[Path, str | None]] = []

            if codigo == "merge":
                out_file = out_dir / "juntado.pdf"
                await asyncio.to_thread(pdf.merge, arquivos, out_file)
                files_to_send.append((out_file, None))

            elif codigo == "split":
                spec = param.get("spec")
                res_files = await asyncio.to_thread(pdf.split, arquivos[0], out_dir, spec)
                files_to_send.extend((f, None) for f in res_files)

            elif codigo == "extract":
                spec = param.get("spec", "")
                out_file = out_dir / "extraido.pdf"
                await asyncio.to_thread(pdf.extract_pages, arquivos[0], out_file, spec)
                files_to_send.append((out_file, None))

            elif codigo == "remove":
                spec = param.get("spec", "")
                out_file = out_dir / "removido.pdf"
                await asyncio.to_thread(pdf.remove_pages, arquivos[0], out_file, spec)
                files_to_send.append((out_file, None))

            elif codigo == "reorder":
                spec = param.get("spec", "")
                out_file = out_dir / "reordenado.pdf"
                await asyncio.to_thread(pdf.reorder, arquivos[0], out_file, spec)
                files_to_send.append((out_file, None))

            elif codigo == "rotate":
                degrees = param.get("degrees", 90)
                out_file = out_dir / "girado.pdf"
                await asyncio.to_thread(pdf.rotate, arquivos[0], out_file, degrees, None)
                files_to_send.append((out_file, None))

            elif codigo == "protect":
                pwd = param.get("password", "")
                out_file = out_dir / "protegido.pdf"
                await asyncio.to_thread(pdf.protect, arquivos[0], out_file, pwd)
                files_to_send.append((out_file, None))

            elif codigo == "unlock":
                pwd = param.get("password", "")
                out_file = out_dir / "desbloqueado.pdf"
                await asyncio.to_thread(pdf.unlock, arquivos[0], out_file, pwd)
                files_to_send.append((out_file, None))

            elif codigo == "watermark":
                texto = param.get("text", "")
                out_file = out_dir / "marca_dagua.pdf"
                await asyncio.to_thread(pdf.watermark_text, arquivos[0], out_file, texto)
                files_to_send.append((out_file, None))

            elif codigo == "page_numbers":
                pos = param.get("position", "bottom-center")
                out_file = out_dir / "numerado.pdf"
                await asyncio.to_thread(pdf.page_numbers, arquivos[0], out_file, 1, pos)
                files_to_send.append((out_file, None))

            elif codigo == "crop_margins":
                mm_val = param.get("mm", 10.0)
                out_file = out_dir / "cortado.pdf"
                await asyncio.to_thread(pdf.crop_margins, arquivos[0], out_file, mm_val)
                files_to_send.append((out_file, None))

            elif codigo == "repair":
                out_file = out_dir / "reparado.pdf"
                await asyncio.to_thread(pdf.repair, arquivos[0], out_file)
                files_to_send.append((out_file, None))

            elif codigo == "images_to_pdf":
                out_file = out_dir / "imagens.pdf"
                await asyncio.to_thread(pdf.images_to_pdf, arquivos, out_file)
                files_to_send.append((out_file, None))

            elif codigo == "compress":
                nivel = param.get("nivel", "recomendada")
                for i, inp_file in enumerate(arquivos, 1):
                    orig_sz = inp_file.stat().st_size
                    out_file = (
                        out_dir / "comprimido.pdf"
                        if len(arquivos) == 1
                        else out_dir / f"comprimido_{i}.pdf"
                    )
                    await asyncio.to_thread(converter.compress, inp_file, out_file, nivel)
                    new_sz = out_file.stat().st_size
                    orig_kb = orig_sz // 1024
                    new_kb = new_sz // 1024
                    pct = round((1 - new_sz / orig_sz) * 100) if orig_sz > 0 else 0
                    caption = f"{orig_kb} KB → {new_kb} KB (-{pct}%)"
                    files_to_send.append((out_file, caption))

            elif codigo == "pdf_to_jpg":
                res_files = await asyncio.to_thread(converter.pdf_to_images, arquivos[0], out_dir, "jpg")
                files_to_send.extend((f, None) for f in res_files)

            elif codigo == "pdf_to_png":
                res_files = await asyncio.to_thread(converter.pdf_to_images, arquivos[0], out_dir, "png")
                files_to_send.extend((f, None) for f in res_files)

            elif codigo == "pdf_to_word":
                out_file = out_dir / "convertido.docx"
                await asyncio.to_thread(converter.pdf_to_word, arquivos[0], out_file)
                files_to_send.append((out_file, None))

            elif codigo == "pdf_to_excel":
                out_file = out_dir / "convertido.xlsx"
                await asyncio.to_thread(converter.pdf_to_excel, arquivos[0], out_file)
                files_to_send.append((out_file, None))

            elif codigo == "pdf_to_pptx":
                out_file = out_dir / "convertido.pptx"
                await asyncio.to_thread(converter.pdf_to_pptx, arquivos[0], out_file)
                files_to_send.append((out_file, None))

            elif codigo == "pdf_to_text":
                out_file = out_dir / "texto.txt"
                await asyncio.to_thread(converter.pdf_to_text, arquivos[0], out_file)
                files_to_send.append((out_file, None))

            elif codigo == "ocr":
                out_file = out_dir / "ocr.pdf"
                await asyncio.to_thread(converter.ocr, arquivos[0], out_file)
                files_to_send.append((out_file, None))

            elif codigo == "pdf_to_pdfa":
                out_file = out_dir / "pdfa.pdf"
                await asyncio.to_thread(converter.pdf_to_pdfa, arquivos[0], out_file)
                files_to_send.append((out_file, None))

            elif codigo == "office_to_pdf":
                for inp_file in arquivos:
                    out_pdf = await asyncio.to_thread(converter.office_to_pdf, inp_file, out_dir)
                    files_to_send.append((out_pdf, None))

            else:
                await chat.send_message("❌ Operação desconhecida.")
                try:
                    await status_msg.delete()
                except Exception:
                    pass
                limpar_sessao(context.user_data)
                return

            if len(files_to_send) > 10:
                zip_path = out_dir / "arquivos.zip"
                with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for f_item, _ in files_to_send:
                        zf.write(f_item, arcname=f_item.name)
                files_to_send = [(zip_path, None)]

            target_msg = update.effective_message
            for f_path, caption in files_to_send:
                sz = f_path.stat().st_size
                if cfg.api_url is None and sz > 50 * 1024 * 1024:
                    await chat.send_message(
                        f"❌ O arquivo gerado ({f_path.name}) possui {sz / (1024*1024):.1f}MB, "
                        "excedendo o limite de envio de 50MB do Telegram sem servidor Bot API local."
                    )
                else:
                    with open(f_path, "rb") as doc_file:
                        try:
                            if target_msg:
                                await target_msg.reply_document(
                                    document=doc_file,
                                    filename=f_path.name,
                                    caption=caption,
                                )
                            else:
                                await chat.send_document(
                                    document=doc_file,
                                    filename=f_path.name,
                                    caption=caption,
                                )
                        except Exception:
                            doc_file.seek(0)
                            await chat.send_document(
                                document=doc_file,
                                filename=f_path.name,
                                caption=caption,
                            )

            try:
                await status_msg.delete()
            except Exception:
                pass
            limpar_sessao(context.user_data)

    except OpError as e:
        try:
            await status_msg.delete()
        except Exception:
            pass
        await chat.send_message(f"❌ {e}")
        limpar_sessao(context.user_data)

    except Exception:
        try:
            await status_msg.delete()
        except Exception:
            pass
        logger.exception("Erro inesperado durante processamento")
        await chat.send_message("❌ Erro inesperado ao processar.")
        limpar_sessao(context.user_data)


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exceção não tratada capturada pelo handler global:", exc_info=context.error)


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    cfg = carregar()

    limpar_pasta_trabalho(cfg.pasta_trabalho)
    get_semaphore(cfg.max_jobs)

    builder = Application.builder().token(cfg.token)
    if cfg.api_url:
        builder = (
            builder.base_url(f"{cfg.api_url}/bot")
            .base_file_url(f"{cfg.api_url}/file/bot")
            .local_mode(True)
        )
    app = builder.build()
    app.bot_data["config"] = cfg

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))
    app.add_handler(CommandHandler("help", cmd_ajuda))
    app.add_handler(CommandHandler("cancelar", cmd_cancelar))
    app.add_handler(CommandHandler("limpar", cmd_limpar))
    app.add_handler(CommandHandler("ferramentas", cmd_ferramentas))
    app.add_handler(CommandHandler("meuid", cmd_meuid))

    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, on_file_received))
    app.add_handler(CallbackQueryHandler(on_callback_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_received))

    app.add_error_handler(global_error_handler)

    logger.info("Bot pronto e iniciando polling...")
    app.run_polling()
