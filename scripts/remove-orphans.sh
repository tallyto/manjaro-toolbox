#!/usr/bin/env bash
set -euo pipefail

orphans=$(pacman -Qdtq 2>/dev/null || true)
if [ -z "$orphans" ]; then
  echo "Nenhum pacote órfão para remover."
  exit 0
fi

echo "Pacotes órfãos que serão removidos:"
echo "$orphans"
echo
sudo pacman -Rns $orphans
