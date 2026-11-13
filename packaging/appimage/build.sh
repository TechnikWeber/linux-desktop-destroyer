#!/usr/bin/env bash
# Builds dist/desktop-destroyer-<version>-x86_64.AppImage (+ .zsync for Gear
# Lever / AppImageUpdate). Meant for CI (see .github/workflows/release.yml),
# works on any x86_64 Linux with curl and FUSE or the extract-and-run fallback.
#
# Base: a relocatable Python from niess/python-appimage, PySide6-Essentials
# from PyPI, then everything Qt Quick/QML/designer is pruned away. Qt
# Multimedia (the sound effects) and Qt DBus (the screenshot portal) stay.
set -euo pipefail

PY=3.12
here="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
root="$(cd "$here/../.." && pwd)"
version="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$root/desktop_destroyer/__init__.py")"
work="$root/build/appimage"
dist="$root/dist"
out="$dist/desktop-destroyer-$version-x86_64.AppImage"
update_info="gh-releases-zsync|TechnikWeber|linux-desktop-destroyer|latest|desktop-destroyer-*-x86_64.AppImage.zsync"

rm -rf "$work"
mkdir -p "$work" "$dist"
cd "$work"
export APPIMAGE_EXTRACT_AND_RUN=1   # no FUSE needed on CI runners

# ---- 1. relocatable Python ------------------------------------------------
# Anonymous API calls share a small limit per IP (CI runners hit it: 403);
# with the workflow's token they count against the repository instead.
auth=()
[ -n "${GITHUB_TOKEN:-}" ] && auth=(-H "Authorization: Bearer $GITHUB_TOKEN")
asset=$(curl -fsSL --retry 3 "${auth[@]}" "https://api.github.com/repos/niess/python-appimage/releases/tags/python$PY" \
    | grep -o "\"name\": *\"python${PY}[^\"]*manylinux_2_28_x86_64.AppImage\"" \
    | head -1 | sed 's/.*"\(python[^"]*\)"/\1/')
[ -n "$asset" ] || { echo "no python $PY AppImage found" >&2; exit 1; }
echo "base: $asset"
curl -fsSL -o python.AppImage "https://github.com/niess/python-appimage/releases/download/python$PY/$asset"
chmod +x python.AppImage
./python.AppImage --appimage-extract >/dev/null
mv squashfs-root AppDir
python_rel="$(cd AppDir && ls -d opt/python$PY/bin/python$PY)"
py="AppDir/$python_rel"

# ---- 2. PySide6 + the app -------------------------------------------------
"$py" -m pip install --no-compile --no-warn-script-location -q -r "$here/requirements.txt"
"$py" -m pip install --no-compile --no-warn-script-location --no-deps -q "$root"
site="$("$py" -c 'import PySide6, os; print(os.path.dirname(PySide6.__file__))')"

# Qt Multimedia (QSoundEffect) lives in PySide6-Addons, 150 MB of mostly 3D,
# charts and web views. Take only the multimedia module and the libraries it
# links, from the Addons wheel of the very same version. Not the FFmpeg media
# plugin: QSoundEffect plays WAV through QAudioSink without it, and the plugin
# wants Qt Quick, which it would then pull from the system's Qt (a mix of two
# Qt builds in one process).
qt_version="$("$py" -c 'import PySide6; print(PySide6.__version__)')"
"$py" -m pip install --no-compile --no-deps -q --target addons "PySide6-Addons==$qt_version"
cp addons/PySide6/QtMultimedia.abi3.so addons/PySide6/QtMultimedia.pyi "$site/"
needed() { readelf -d "$1" | sed -n 's/.*(NEEDED).*\[\(.*\)\]/\1/p'; }
queue=("$site/QtMultimedia.abi3.so")
while [ ${#queue[@]} -gt 0 ]; do
    file="${queue[0]}"; queue=("${queue[@]:1}")
    while read -r lib; do
        if [ -e "addons/PySide6/Qt/lib/$lib" ] && [ ! -e "$site/Qt/lib/$lib" ]; then
            cp "addons/PySide6/Qt/lib/$lib" "$site/Qt/lib/"
            queue+=("$site/Qt/lib/$lib")
        fi
    done < <(needed "$file")
done
rm -rf addons
# only check the files here: the build host may lack libEGL/libpulse; the
# real import runs in the --selftest on Fedora afterwards
[ -e "$site/Qt/lib/libQt6Multimedia.so.6" ] || { echo "QtMultimedia library missing" >&2; exit 1; }

# ---- 3. prune what this app never loads -----------------------------------
(
    cd "$site"
    rm -rf Qt/qml Qt/translations Qt/libexec include typesystems glue scripts \
           designer linguist assistant lupdate lrelease qmllint qmlformat qmlls \
           qmlcachegen qmltyperegistrar qmlimportscanner rcc uic balsam* \
           Qt/plugins/{qmltooling,sqldrivers,designer,qmllint}
    for lib in Quick Qml Pdf Designer Help Sql Test ShaderTools VirtualKeyboard \
               LabsAnimation LabsFolderListModel LabsQmlModels LabsSettings \
               LabsSharedImage LabsWavefrontMesh LabsPlatform QmlModels; do
        rm -f Qt/lib/libQt6"$lib"*.so* Qt"$lib"*.abi3.so Qt"$lib"*.pyi
    done
)
find AppDir -name '__pycache__' -prune -exec rm -rf {} +
rm -rf AppDir/opt/python$PY/lib/python$PY/{test,idlelib,tkinter,ensurepip,lib2to3}

# ---- 4. AppImage metadata -------------------------------------------------
rm -f AppDir/*.desktop AppDir/*.png AppDir/*.svg AppDir/.DirIcon AppDir/usr/share/metainfo/*.xml
# python-appimage ships AppRun as a symlink into usr/bin; writing through it
# would clobber the target, so replace the link with a real file
rm -f AppDir/AppRun
cat > AppDir/AppRun <<EOF
#!/bin/bash
# -I: ignore PYTHONPATH and user site-packages, only use what is bundled
here="\${APPDIR:-\$(dirname "\$(readlink -f "\${0}")")}"
exec "\$here/$python_rel" -I -m desktop_destroyer "\$@"
EOF
chmod +x AppDir/AppRun
install -Dm644 "$root/share/desktop-destroyer.desktop" AppDir/desktop-destroyer.desktop
install -Dm644 "$root/share/desktop-destroyer.desktop" AppDir/usr/share/applications/desktop-destroyer.desktop
install -Dm644 "$root/share/desktop-destroyer.png" AppDir/desktop-destroyer.png
for size in 128 64 48; do
    install -Dm644 "$root/share/desktop-destroyer-$size.png" \
        "AppDir/usr/share/icons/hicolor/${size}x${size}/apps/desktop-destroyer.png"
done
install -Dm644 "$root/share/desktop-destroyer.png" AppDir/usr/share/icons/hicolor/256x256/apps/desktop-destroyer.png
ln -sf desktop-destroyer.png AppDir/.DirIcon
install -Dm644 "$root/share/io.github.technikweber.desktop-destroyer.metainfo.xml" \
    AppDir/usr/share/metainfo/io.github.technikweber.desktop-destroyer.appdata.xml

# python-appimage extracts with 0700 directories; the AppImage must be
# readable for every user
chmod -R a+rX AppDir

# ---- 5. pack --------------------------------------------------------------
curl -fsSL -o appimagetool \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool
rm -f "$out" "$out.zsync"
ARCH=x86_64 ./appimagetool --no-appstream -u "$update_info" AppDir "$out"
mv -f "$(basename "$out").zsync" "$dist/" 2>/dev/null || true
ls -lh "$dist"
