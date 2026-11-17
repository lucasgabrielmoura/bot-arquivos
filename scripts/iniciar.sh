#!/usr/bin/env bash
# Mantem o bot rodando: se cair (sem internet, erro), reinicia em 10s.
cd "$(dirname "$0")/.."
while true; do
  ./venv/bin/python -m bot
  echo ">> Bot parou (codigo $?). Reiniciando em 10s... (Ctrl+C para sair)"
  sleep 10
done
