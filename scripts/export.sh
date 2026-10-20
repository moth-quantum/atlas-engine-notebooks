#!/usr/bin/env bash
# Run an engine notebook headlessly against the Moth API and save code + outputs.
#   MOTH_API_KEY=... scripts/export.sh blur
# Writes <engine>/outputs/<engine>_notebook.ipynb and .html. Needs: pip install -r requirements.txt
set -euo pipefail
engine="${1:?usage: scripts/export.sh <engine>}"
cd "$(dirname "$0")/../$engine"
: "${MOTH_API_KEY:?set MOTH_API_KEY (Atlas → API keys)}"
mkdir -p outputs
export MOTH_AUTORUN=1
marimo export ipynb --include-outputs --no-sandbox -o "outputs/${engine}_notebook.ipynb" "${engine}_notebook.py"
marimo export html --no-sandbox -o "outputs/${engine}_notebook.html" "${engine}_notebook.py"
echo "wrote $engine/outputs/${engine}_notebook.{ipynb,html}"
