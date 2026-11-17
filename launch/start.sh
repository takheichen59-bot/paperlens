#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install '.[platform]'
printf '%s\n' 'Open http://127.0.0.1:8765 after startup. Ctrl+C to stop.'
exec .venv/bin/python -m science_platform serve
