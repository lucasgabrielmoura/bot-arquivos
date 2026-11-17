from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Config:
    token: str
    usuarios: frozenset[int]
    pasta_trabalho: Path
    max_jobs: int
    api_url: str | None = None


def carregar() -> Config:
    load_dotenv()

    token = os.getenv("BOT_TOKEN")
    if not token or not token.strip():
        raise SystemExit("Erro: Variável de ambiente BOT_TOKEN é obrigatória.")
    token = token.strip()

    allowed_raw = os.getenv("ALLOWED_USERS", "").strip()
    if allowed_raw:
        usuarios_list: list[int] = []
        for uid_str in allowed_raw.split(","):
            uid_str = uid_str.strip()
            if uid_str:
                try:
                    usuarios_list.append(int(uid_str))
                except ValueError:
                    logger.warning("ID de usuário inválido em ALLOWED_USERS: %s", uid_str)
        usuarios = frozenset(usuarios_list)
    else:
        usuarios = frozenset()

    if not usuarios:
        logger.warning("nenhum usuario liberado")

    work_dir_raw = os.getenv("WORK_DIR", "./tmp_trabalho").strip()
    pasta_trabalho = Path(work_dir_raw if work_dir_raw else "./tmp_trabalho").resolve()

    max_jobs_raw = os.getenv("MAX_JOBS", "1").strip()
    try:
        max_jobs = int(max_jobs_raw) if max_jobs_raw else 1
    except ValueError:
        max_jobs = 1

    api_url_raw = os.getenv("TELEGRAM_API_URL")
    if api_url_raw and api_url_raw.strip():
        api_url = api_url_raw.strip().rstrip("/")
    else:
        api_url = None

    return Config(
        token=token,
        usuarios=usuarios,
        pasta_trabalho=pasta_trabalho,
        max_jobs=max_jobs,
        api_url=api_url,
    )
