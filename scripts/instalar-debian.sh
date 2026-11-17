#!/usr/bin/env bash
# Instala o bot DENTRO do Debian (proot-distro) no Termux, ou em qualquer Debian/Ubuntu.
# Uso: bash scripts/instalar-debian.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo ">> Pacotes do sistema (LibreOffice sem interface, Ghostscript, OCR, qpdf)..."
apt update
apt install -y --no-install-recommends \
  python3 python3-venv python3-pip \
  ghostscript qpdf ocrmypdf tesseract-ocr-por tesseract-ocr-eng \
  libreoffice-core-nogui libreoffice-writer-nogui libreoffice-calc-nogui libreoffice-impress-nogui \
  fonts-dejavu fonts-liberation2 \
  python3-fitz python3-pil

echo ">> Ambiente Python..."
# --system-site-packages: aproveita PyMuPDF/Pillow do apt em celulares 32-bit sem wheel pronta
python3 -m venv --system-site-packages venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo ">> Criei o .env. Edite com: nano .env  (BOT_TOKEN e ALLOWED_USERS)"
fi
echo ">> Pronto. Inicie com: bash scripts/iniciar.sh"
