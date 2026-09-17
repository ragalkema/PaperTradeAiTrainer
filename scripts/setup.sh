#!/usr/bin/env sh
set -eu

python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e "./backend[dev]"
npm ci --prefix frontend

echo "Setup complete. Copy .env.example to .env before running services."
