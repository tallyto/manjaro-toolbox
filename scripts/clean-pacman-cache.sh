#!/usr/bin/env bash
set -euo pipefail

if ! command -v paccache >/dev/null 2>&1; then
  echo "paccache não encontrado. Instalando pacman-contrib..."
  sudo pacman -S --needed pacman-contrib
fi

echo "Limpando cache antigo de pacotes instalados, mantendo 2 versões..."
sudo paccache -rk2

echo
echo "Limpando cache de pacotes desinstalados..."
sudo paccache -ruk0
