"""Wiring: grab the desktop, open a window per screen, share one arsenal."""

from __future__ import annotations

import argparse
import os
import sys
import time

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from . import __version__, capture
from .sfx import Sfx
from .weapons import build_arsenal
from .window import DestroyerWindow


class Session(QObject):
    """State shared by every screen: the arsenal, the sound bank, the windows."""

    def __init__(self, muted: bool = False) -> None:
        super().__init__()
        self.arsenal = build_arsenal()
        self.index = 0
        self.sfx = Sfx(enabled=not muted)
        self.windows: list[DestroyerWindow] = []

    @property
    def current(self):
        return self.arsenal[self.index]

    # -- commands ----------------------------------------------------------

    def select(self, index: int) -> None:
        if not 0 <= index < len(self.arsenal) or index == self.index:
            return
        for window in self.windows:
            self.current.deactivate(window)
        self.index = index
        for window in self.windows:
            window.pressed = False
            window.toast(f"{self.current.number}: {self.current.label}", 1.4)
            window.mark_all()

    def toggle_toolbox(self) -> None:
        for window in self.windows:
            window.toolbox.visible = not window.toolbox.visible
            window.mark_all()

    def repair(self) -> None:
        for window in self.windows:
            window.repair_all()
            window.toast("Desktop repariert.", 1.6)

    def save(self) -> None:
        saved = [window.save_shot() for window in self.windows]
        first = next((path for path in saved if path), None)
        message = f"Gespeichert: {first}" if first else "Speichern fehlgeschlagen."
        for window in self.windows:
            window.toast(message, 3.2)

    def toggle_sound(self) -> None:
        self.sfx.set_enabled(not self.sfx.enabled)
        state = "an" if self.sfx.enabled else "aus"
        for window in self.windows:
            window.toast(f"Ton {state}.", 1.4)

    def quit(self) -> None:
        self.sfx.stop_all_loops()
        for window in self.windows:
            window.timer.stop()
            window.close()
        QApplication.quit()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="desktop-destroyer",
        description="Smash, burn and saw your Linux desktop to pieces.",
    )
    parser.add_argument("--version", action="version",
                        version=f"desktop-destroyer {__version__}")
    parser.add_argument("-w", "--windowed", action="store_true",
                        help="run in a normal window instead of fullscreen")
    parser.add_argument("-i", "--image", metavar="FILE",
                        help="destroy this image instead of a live screenshot")
    parser.add_argument("-m", "--mute", action="store_true", help="start muted")
    parser.add_argument("-d", "--delay", type=float, default=0.0, metavar="SECONDS",
                        help="wait before grabbing the desktop")
    parser.add_argument("--primary-only", action="store_true",
                        help="only take over the primary screen")
    parser.add_argument("--backend", action="store_true",
                        help="print the detected capture backend and exit")
    parser.add_argument("--selftest", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def selftest(app: QApplication) -> int:
    """Build one window on a stand-in desktop, check Qt Multimedia, quit.

    Used by CI on the AppImage and the RPM: a module pruned too eagerly or a
    missing Qt plugin shows up here instead of on someone's desktop.
    """
    from PySide6.QtCore import QTimer

    problems = []
    try:
        from PySide6.QtMultimedia import QSoundEffect  # noqa: F401
    except ImportError as exc:
        problems.append(f"QtMultimedia missing: {exc}")
    try:
        from PySide6.QtDBus import QDBusConnection  # noqa: F401
    except ImportError as exc:
        problems.append(f"QtDBus missing: {exc}")

    # never a real screenshot here: the stand-in desktop is enough
    screen = app.primaryScreen()
    shot = capture._fallback_wallpaper(screen.geometry().size())
    session = Session(muted=False)
    window = DestroyerWindow(session, shot, screen, windowed=True)
    session.windows.append(window)
    window.show()

    def report() -> None:
        ok = not problems
        sound = "ready" if session.sfx._ready else "no audio output"
        print(f"selftest {'ok' if ok else 'FAILED'}: desktop-destroyer {__version__}, "
              f"Qt {app.platformName()}, window built, sound {sound}"
              + "".join(f"\n  {p}" for p in problems))
        session.quit()
        app.exit(0 if ok else 1)

    QTimer.singleShot(500, report)
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    options = parse_args(sys.argv[1:] if argv is None else argv)
    if options.selftest:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    QApplication.setApplicationName("Desktop Destroyer")
    QApplication.setApplicationVersion(__version__)
    QGuiApplication.setDesktopFileName("desktop-destroyer")
    app = QApplication(sys.argv[:1])

    if options.selftest:
        return selftest(app)

    if options.backend:
        image, backend = capture.grab_virtual_desktop()
        size = f"{image.width()}x{image.height()}" if image is not None else "-"
        print(f"session={capture.session_type()} backend={backend} size={size}")
        return 0

    if options.delay > 0:
        # nothing is on screen yet, so simply waiting is fine here
        time.sleep(options.delay)

    screens = app.screens()
    if options.primary_only or options.windowed:
        screens = [app.primaryScreen()]

    shots, backend = capture.capture(screens, options.image)
    if backend == "fallback":
        print("desktop-destroyer: no screenshot backend worked -- using a stand-in "
              "desktop.\n  Wayland users: install 'grim' (wlroots), 'spectacle' (KDE) "
              "or an xdg-desktop-portal.", file=sys.stderr)

    session = Session(muted=options.mute)
    for screen in screens:
        window = DestroyerWindow(session, shots[screen.name()], screen,
                                 windowed=options.windowed)
        session.windows.append(window)

    for window in session.windows:
        window.show()
        window.raise_()
        window.activateWindow()

    return app.exec()
