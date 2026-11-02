#!/bin/zsh
set -eu
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
swiftc OsmoStudio/tools/render_raw.swift -o OsmoStudio/tools/render_raw -framework CoreImage -framework AppKit
(cd OsmoStudio && ./build-mac.sh)
(cd SimpleSuperresolution && ./build-mac.sh)
