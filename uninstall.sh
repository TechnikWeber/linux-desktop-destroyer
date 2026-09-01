#!/usr/bin/env bash
# Removes the menu entry, the icons and the PATH symlink. The repo itself and
# ~/.cache/desktop-destroyer stay put -- delete those by hand if you want.
set -euo pipefail

apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
icons="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"

rm -f "$apps/desktop-destroyer.desktop"
rm -f "$HOME/.local/bin/desktop-destroyer"
for size in 256 128 64 48; do
    rm -f "$icons/${size}x${size}/apps/desktop-destroyer.png"
done

command -v update-desktop-database >/dev/null && update-desktop-database "$apps" 2>/dev/null || true
command -v kbuildsycoca6           >/dev/null && kbuildsycoca6 --noincremental 2>/dev/null || true
echo "Removed from the application menu."
