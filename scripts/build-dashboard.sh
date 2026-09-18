#!/usr/bin/env sh
set -eu
repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repository_root"
python -m pip install -e '.[build]'
python -m PyInstaller --noconfirm --clean Dashboard/PaperTradeAiTrainer.spec
printf 'Built %s\n' "$repository_root/dist/PaperTradeAiTrainer/PaperTradeAiTrainer"
