#!/usr/bin/env bash
set -euo pipefail

echo "== Sistema =="
uname -a

echo
if command -v lsb_release >/dev/null 2>&1; then
  lsb_release -a 2>/dev/null || true
fi

echo
if command -v df >/dev/null 2>&1; then
  echo "== Espaço em disco =="
  df -h
fi

echo
if [ -d "$HOME/.cache" ]; then
  echo "== Cache do usuário =="
  du -sh "$HOME/.cache" 2>/dev/null || true
fi

echo
if [ -d /var/cache/pacman/pkg ]; then
  echo "== Cache do Pacman =="
  du -sh /var/cache/pacman/pkg 2>/dev/null || true
fi

echo
if command -v pacman >/dev/null 2>&1; then
  echo "== Pacotes órfãos =="
  pacman -Qdtq 2>/dev/null || echo "Nenhum pacote órfão encontrado."
fi
