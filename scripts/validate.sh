#!/usr/bin/env sh
set -eu

.venv/bin/python validation/architecture/check_boundaries.py
.venv/bin/python validation/environment/check_environment.py
docker compose config --quiet
echo "Repository validation passed."
