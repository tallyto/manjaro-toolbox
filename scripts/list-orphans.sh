#!/usr/bin/env bash
set -euo pipefail

if ! command -v pacman >/dev/null 2>&1; then
  echo "pacman não encontrado."
  exit 1
fi

orphans=$(pacman -Qdtq 2>/dev/null || true)
if [ -z "$orphans" ]; then
  echo "Nenhum pacote órfão encontrado."
else
  echo "$orphans"
fi
