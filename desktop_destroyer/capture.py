"""Grab a still of the real desktop -- the canvas we are about to ruin.

Every backend returns one QImage of the whole virtual desktop; ``capture()``
then slices it up per screen.  The chain covers X11, wlroots, KDE, GNOME and
finally the XDG desktop portal, which works anywhere a portal is installed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from PySide6.QtCore import QEventLoop, QRect, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter


def session_type() -> str:
    """``"wayland"``, ``"x11"`` or ``"unknown"``."""
    kind = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if kind in ("wayland", "x11"):
        return kind
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"


def _tmp_png() -> str:
    fd, path = tempfile.mkstemp(prefix="desktop-destroyer-", suffix=".png")
    os.close(fd)
    os.unlink(path)  # the tools want to create the file themselves
    return path


def _load_and_unlink(path: str) -> QImage | None:
    try:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return None
        image = QImage(path)
        return None if image.isNull() else image
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _run(argv: list[str], timeout: float = 8.0) -> bool:
    try:
        done = subprocess.run(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
        )
        return done.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


# --------------------------------------------------------------------------
# backends -- each returns a QImage of the full virtual desktop, or None
# --------------------------------------------------------------------------


def _grab_qt() -> QImage | None:
    """Qt's own root-window grab.  Instant on X11, a black frame on Wayland."""
    screens = QGuiApplication.screens()
    if not screens:
        return None
    virtual = screens[0].virtualGeometry()
    canvas = QImage(virtual.size(), QImage.Format_RGB32)
    canvas.fill(QColor("black"))
    painter = QPainter(canvas)
    got_one = False
    for screen in screens:
        shot = screen.grabWindow(0)
        if shot.isNull():
            continue
        geometry = screen.geometry().translated(-virtual.topLeft())
        painter.drawPixmap(geometry, shot)
        got_one = True
    painter.end()
    return canvas if got_one else None


def _grab_grim() -> QImage | None:
    """wlroots compositors: sway, Hyprland, river, Wayfire, labwc ..."""
    if not shutil.which("grim"):
        return None
    path = _tmp_png()
    return _load_and_unlink(path) if _run(["grim", path]) else None


def _grab_spectacle() -> QImage | None:
    """KDE Plasma.  ``-b`` keeps it headless, ``-n`` kills the notification."""
    if not shutil.which("spectacle"):
        return None
    path = _tmp_png()
    ok = _run(["spectacle", "-b", "-n", "-f", "-o", path], timeout=15.0)
    return _load_and_unlink(path) if ok else None


def _grab_gnome_shell() -> QImage | None:
    """GNOME's private interface -- no portal dialog, no permission prompt."""
    if not shutil.which("gdbus") or "gnome" not in os.environ.get(
        "XDG_CURRENT_DESKTOP", ""
    ).lower():
        return None
    path = _tmp_png()
    ok = _run(
        [
            "gdbus", "call", "--session",
            "--dest", "org.gnome.Shell.Screenshot",
            "--object-path", "/org/gnome/Shell/Screenshot",
            "--method", "org.gnome.Shell.Screenshot.Screenshot",
            "false", "false", path,
        ]
    )
    return _load_and_unlink(path) if ok else None


def _grab_gnome_screenshot() -> QImage | None:
    if not shutil.which("gnome-screenshot"):
        return None
    path = _tmp_png()
    return _load_and_unlink(path) if _run(["gnome-screenshot", "-f", path]) else None


def _grab_imagemagick() -> QImage | None:
    """X11 leftovers, in case Qt's grab came up empty."""
    for tool, argv in (
        ("maim", ["maim"]),
        ("scrot", ["scrot", "-o"]),
        ("import", ["import", "-window", "root"]),
    ):
        if not shutil.which(tool):
            continue
        path = _tmp_png()
        if _run(argv + [path]):
            image = _load_and_unlink(path)
            if image is not None:
                return image
    return None


def _grab_portal() -> QImage | None:
    """org.freedesktop.portal.Screenshot -- the universal fallback.

    Some compositors show a one-off confirmation dialog here; that is the
    price of a backend that works absolutely everywhere.
    """
    try:
        from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
    except ImportError:
        return None

    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        return None

    token = f"desktop_destroyer_{os.getpid()}"
    sender = bus.baseService().lstrip(":").replace(".", "_")
    request_path = f"/org/freedesktop/portal/desktop/request/{sender}/{token}"

    loop = QEventLoop()
    result: dict[str, str] = {}

    def on_response(message: QDBusMessage) -> None:
        args = message.arguments()
        if len(args) >= 2 and args[0] == 0:
            uri = (args[1] or {}).get("uri", "")
            if uri:
                result["uri"] = uri
        loop.quit()

    bus.connect(
        "", request_path, "org.freedesktop.portal.Request", "Response", on_response
    )

    portal = QDBusInterface(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.Screenshot",
        bus,
    )
    if not portal.isValid():
        return None

    reply = portal.call(
        "Screenshot", "", {"handle_token": token, "interactive": False}
    )
    if reply.type() == QDBusMessage.ErrorMessage:
        return None

    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    timeout.start(30_000)
    loop.exec()
    timeout.stop()

    uri = result.get("uri")
    if not uri:
        return None
    path = QUrl(uri).toLocalFile()
    if not path or not os.path.exists(path):
        return None
    image = QImage(path)
    if path.startswith(tempfile.gettempdir()) or "/Screenshots/" in path:
        try:
            os.unlink(path)  # the portal hands us a throwaway file
        except OSError:
            pass
    return None if image.isNull() else image


def _fallback_wallpaper(size) -> QImage:
    """No backend worked -- hand back something plausible to smash anyway."""
    image = QImage(size, QImage.Format_RGB32)
    gradient = QLinearGradient(0, 0, size.width() * 0.4, size.height())
    gradient.setColorAt(0.0, QColor(58, 78, 122))
    gradient.setColorAt(0.55, QColor(32, 44, 74))
    gradient.setColorAt(1.0, QColor(16, 20, 36))
    painter = QPainter(image)
    painter.fillRect(image.rect(), gradient)
    painter.setPen(QColor(255, 255, 255, 26))
    for i in range(0, size.width(), 90):
        painter.drawLine(i, 0, i - size.height() // 3, size.height())
    painter.end()
    return image


_WAYLAND_CHAIN = (
    ("grim", _grab_grim),
    ("spectacle", _grab_spectacle),
    ("gnome-shell", _grab_gnome_shell),
    ("gnome-screenshot", _grab_gnome_screenshot),
    ("xdg-portal", _grab_portal),
)

_X11_CHAIN = (
    ("qt", _grab_qt),
    ("imagemagick", _grab_imagemagick),
    ("xdg-portal", _grab_portal),
)


def grab_virtual_desktop() -> tuple[QImage | None, str]:
    """Try every backend that fits this session.  Returns (image, backend)."""
    chain = _WAYLAND_CHAIN if session_type() == "wayland" else _X11_CHAIN
    for name, backend in chain:
        try:
            image = backend()
        except Exception:  # a broken backend must never take the app down
            image = None
        if image is not None and not image.isNull() and image.width() > 1:
            return image, name
    return None, "none"


def slice_per_screen(image: QImage, screens) -> dict[str, QImage]:
    """Cut the virtual-desktop grab into one image per physical screen.

    Screen geometry is in logical pixels but the grab is in physical ones, so
    each piece keeps its native resolution and carries the ratio along -- on a
    HiDPI display that is the difference between crisp and mushy.
    """
    virtual = screens[0].virtualGeometry()
    scale = image.width() / max(1, virtual.width())
    pieces: dict[str, QImage] = {}
    for screen in screens:
        ratio = max(1.0, screen.devicePixelRatio())
        local = screen.geometry().translated(-virtual.topLeft())
        source = QRect(
            round(local.x() * scale),
            round(local.y() * scale),
            round(local.width() * scale),
            round(local.height() * scale),
        ).intersected(image.rect())
        piece = image.copy(source) if not source.isEmpty() else QImage()

        wanted = QSize(round(local.width() * ratio), round(local.height() * ratio))
        if piece.isNull():
            piece = _fallback_wallpaper(wanted)
        elif piece.size() != wanted:
            piece = piece.scaled(wanted, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        piece = piece.convertToFormat(QImage.Format_RGB32)
        piece.setDevicePixelRatio(ratio)
        pieces[screen.name()] = piece
    return pieces


def capture(screens, source_file: str | None = None) -> tuple[dict[str, QImage], str]:
    """Desktop shot for every screen, plus the name of the backend used."""
    if source_file:
        image = QImage(source_file)
        if image.isNull():
            raise SystemExit(f"desktop-destroyer: cannot read image {source_file!r}")
        pieces = {}
        for screen in screens:
            ratio = max(1.0, screen.devicePixelRatio())
            size = QSize(round(screen.geometry().width() * ratio),
                         round(screen.geometry().height() * ratio))
            piece = image.scaled(size, Qt.IgnoreAspectRatio,
                                 Qt.SmoothTransformation).convertToFormat(
                QImage.Format_RGB32)
            piece.setDevicePixelRatio(ratio)
            pieces[screen.name()] = piece
        return pieces, "file"

    image, backend = grab_virtual_desktop()
    if image is None:
        pieces = {}
        for screen in screens:
            ratio = max(1.0, screen.devicePixelRatio())
            piece = _fallback_wallpaper(QSize(
                round(screen.geometry().width() * ratio),
                round(screen.geometry().height() * ratio)))
            piece.setDevicePixelRatio(ratio)
            pieces[screen.name()] = piece
        return pieces, "fallback"
    return slice_per_screen(image, screens), backend
