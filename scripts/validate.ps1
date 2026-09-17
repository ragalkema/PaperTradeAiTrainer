$ErrorActionPreference = "Stop"

& .\.venv\Scripts\python.exe validation\architecture\check_boundaries.py
& .\.venv\Scripts\python.exe validation\environment\check_environment.py
docker compose config --quiet
Write-Host "Repository validation passed."
