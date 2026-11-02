#!/bin/zsh
set -e
cd "$(dirname "$0")"
APP="$PWD/Osmo Studio.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" build-cache
swiftc -parse-as-library -swift-version 5 -module-cache-path "$PWD/build-cache" -O mac/OsmoStudio.swift -o "$APP/Contents/MacOS/OsmoStudio" -framework SwiftUI -framework AppKit -framework CoreImage
cp Info.plist "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Print' "$APP/Contents/Info.plist" >/dev/null
codesign --force --sign - "$APP"
