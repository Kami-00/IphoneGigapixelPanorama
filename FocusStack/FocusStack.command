#!/bin/zsh
set -e
cd "$(dirname "$0")"
PYTHON="${FOCUSSTACK_PYTHON:-$PWD/../.venv/bin/python}"
if [[ $# -gt 0 ]]; then
  INPUT="$1"
else
  INPUT="$(osascript -e 'POSIX path of (choose folder with prompt "Ordner mit den Focus-Stacking-Aufnahmen auswählen" default location (path to desktop folder))')"
fi
OUTPUT="${INPUT%/}/FocusStack-$(date +%Y%m%d-%H%M%S)"
"$PYTHON" focus_stack.py "$INPUT" --output "$OUTPUT"
open "$OUTPUT/Vergleich.html"
