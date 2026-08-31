"""Wiring: grab the desktop, open a window per screen, share one arsenal."""

from __future__ import annotations

import argparse
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    options = parse_args(sys.argv[1:] if argv is None else argv)

    QApplication.setApplicationName("Desktop Destroyer")
    QApplication.setApplicationVersion(__version__)
    QGuiApplication.setDesktopFileName("desktop-destroyer")
    app = QApplication(sys.argv)

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
