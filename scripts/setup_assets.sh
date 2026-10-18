#!/usr/bin/env bash
# Baixa os datasets de fotos de coral (Kaggle, sem login) e monta as pastas de fotos usadas pelos mundos.
# Rode UMA vez, no seu computador (fora do container), na raiz do repositório:
#     ./scripts/setup_assets.sh
# Cria um ambiente virtual em .venv-assets/ (não suja o Python do sistema) e baixa ~60 MB em datasets/.
# Fotos criadas (ambas fora do git): models/coral_textures/ (coral_world_textura) e
# models/coral_textures_prova/ (coral_world_prova).
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v python3 >/dev/null; then
  echo "python3 não encontrado. Instale com: sudo apt install python3 python3-venv" >&2; exit 1
fi
if [ ! -d .venv-assets ]; then
  python3 -m venv .venv-assets || { echo "Falhou criar o ambiente virtual. Instale com: sudo apt install python3-venv" >&2; exit 1; }
fi
.venv-assets/bin/pip install -q --disable-pip-version-check pillow numpy kagglehub

DATASETS="${DATASETS:-datasets}"
echo "== fotos do mundo coral_world_textura (baixa os datasets em ${DATASETS}/)"
.venv-assets/bin/python scripts/setup_coral_textures.py --download --datasets "$DATASETS"
echo "== fotos do mundo coral_world_prova"
.venv-assets/bin/python scripts/setup_photos_prova.py --datasets "$DATASETS"
echo "Pronto. Agora compile e rode no container (veja o README)."
