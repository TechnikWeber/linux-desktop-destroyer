#!/usr/bin/env bash
# Creates a self-contained .venv next to this script, so the game runs
# without touching anything system-wide.
set -euo pipefail
here="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
cd "$here"

if python3 -c "import PySide6" 2>/dev/null; then
    echo "PySide6 is already available system-wide -- nothing to install."
    echo "Start it with:  ./desktop-destroyer"
    exit 0
fi

echo "Creating $here/.venv ..."
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip >/dev/null
./.venv/bin/pip install "PySide6>=6.5"
echo
echo "Done. Start it with:  ./desktop-destroyer"
