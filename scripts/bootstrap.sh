#!/usr/bin/env bash
set -euo pipefail

PY="${PYTHON:-python}"

echo "[bootstrap] creating venv"
$PY -m venv .venv

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[bootstrap] installing deps"
pip install --upgrade pip
pip install -e ".[dev]"

if [ ! -f .env ]; then
  echo "[bootstrap] creating .env from .env.example"
  cp .env.example .env
fi

echo "[bootstrap] running health check (server must be running separately)"
echo "[bootstrap]    uvicorn app.main:app --reload --port 8000"
