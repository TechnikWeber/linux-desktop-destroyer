#!/usr/bin/env bash
# Puts Desktop Destroyer into the application menu, so it can be started with
# a click, and makes sure PySide6 is available.
set -euo pipefail

here="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
cd "$here"

apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
icons="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
bin="$HOME/.local/bin"

# ---- 1. dependency -------------------------------------------------------
if python3 -c "import PySide6" 2>/dev/null; then
    echo "PySide6: already available system-wide."
else
    echo "PySide6 is missing. Your distribution's package is the lighter option:"
    echo "  Fedora/RHEL  sudo dnf install python3-pyside6"
    echo "  Debian/Ubuntu sudo apt install python3-pyside6"
    echo "  Arch          sudo pacman -S pyside6"
    echo
    read -r -p "Install a local copy into $here/.venv instead? [y/N] " reply
    case "$reply" in
        [yY]*)
            python3 -m venv .venv
            ./.venv/bin/pip install --upgrade pip >/dev/null
            ./.venv/bin/pip install "PySide6>=6.5"
            ;;
        *)  echo "Skipped. Install PySide6, then run this script again."; exit 1 ;;
    esac
fi

# ---- 2. menu entry, icon, and a plain 'desktop-destroyer' command ---------
mkdir -p "$apps" "$bin"
for size in 256 128 64 48; do
    src="share/desktop-destroyer.png"
    [[ $size != 256 ]] && src="share/desktop-destroyer-$size.png"
    mkdir -p "$icons/${size}x${size}/apps"
    install -m644 "$src" "$icons/${size}x${size}/apps/desktop-destroyer.png"
done

# the launcher is not on PATH from the menu's point of view, so bake in the path
sed "s|^Exec=.*|Exec=$here/desktop-destroyer|" desktop-destroyer.desktop \
    > "$apps/desktop-destroyer.desktop"
chmod 644 "$apps/desktop-destroyer.desktop"
ln -sf "$here/desktop-destroyer" "$bin/desktop-destroyer"

# ---- 3. nudge the desktop into noticing ----------------------------------
command -v update-desktop-database >/dev/null && update-desktop-database "$apps" 2>/dev/null || true
command -v gtk-update-icon-cache   >/dev/null && gtk-update-icon-cache -qtf "$icons" 2>/dev/null || true
command -v kbuildsycoca6           >/dev/null && kbuildsycoca6 --noincremental 2>/dev/null || true

cat <<MSG

Done.

  * Application menu: search for "Desktop Destroyer" and click it.
  * Terminal:         desktop-destroyer

Remove again with ./uninstall.sh
MSG
