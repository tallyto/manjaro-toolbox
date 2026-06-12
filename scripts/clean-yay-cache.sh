#!/usr/bin/env bash
set -euo pipefail

if ! command -v yay >/dev/null 2>&1; then
  echo "yay não está instalado. Nada a limpar."
  exit 0
fi

yay -Sc
