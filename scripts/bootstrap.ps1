$ErrorActionPreference = "Stop"

$python = $env:PYTHON
if (-not $python) { $python = "python" }

Write-Host "[bootstrap] creating venv"
& $python -m venv .venv

. .\.venv\Scripts\Activate.ps1

Write-Host "[bootstrap] installing deps"
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

if (-not (Test-Path .env)) {
  Write-Host "[bootstrap] creating .env from .env.example"
  Copy-Item .env.example .env
}

Write-Host "[bootstrap] run the API in another terminal: uvicorn app.main:app --reload --port 8000"
