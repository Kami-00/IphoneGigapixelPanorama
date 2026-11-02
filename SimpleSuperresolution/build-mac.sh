#!/bin/zsh
set -eu
cd "$(dirname "$0")"
APP="$PWD/Superresolution.app"
mkdir -p "$APP/Contents/MacOS" build-cache
cp Info.plist "$APP/Contents/Info.plist"
swiftc -parse-as-library -swift-version 5 -module-cache-path "$PWD/build-cache" -O Superresolution.swift -o "$APP/Contents/MacOS/Superresolution" -framework SwiftUI -framework AppKit
codesign --force --sign - "$APP"
