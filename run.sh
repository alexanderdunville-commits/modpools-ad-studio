#!/usr/bin/env bash
# Start Modpools Ad Studio locally.
# Creates a virtualenv on first run, installs deps, and launches the server.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment…"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing dependencies…"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if [ ! -f ".env" ]; then
  echo "No .env found — copy .env.example to .env and add your ANTHROPIC_API_KEY."
fi

echo "Starting on http://localhost:8000 …"
exec uvicorn app.main:app --reload --port 8000
