"""One fullscreen window per monitor -- the desktop you are about to ruin.

The screenshot is shown pixel-for-pixel where the real desktop was, so the
illusion holds the moment the window maps.  ``canvas`` is the working copy that
gets shot, burned and sawn; ``pristine`` is kept untouched so the washing gun
has something to restore from.
"""

from __future__ import annotations

import datetime as _dt
import math
import os
import random
from contextlib import contextmanager
from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRegion,
)
from PySide6.QtWidgets import QWidget

from .fx import bite_path, draw_particles
from .toolbox import Toolbox
from .weapons import VOID

rng = random.Random()

MAX_PARTICLES = 900
HINT_SECONDS = 7.0

DEFAULT_HINT = (
    "Zerlege deinen Desktop!   1–9 Waffen   ·   Tab Werkzeugkasten   ·   "
    "R Reparieren   ·   S Speichern   ·   Esc Beenden"
)


class DestroyerWindow(QWidget):
    def __init__(self, session, shot: QImage, screen=None, windowed: bool = False):
        super().__init__()
        self.session = session
        self.windowed = windowed

        ratio = max(1.0, shot.devicePixelRatio())
        self.pristine = shot.convertToFormat(QImage.Format_ARGB32_Premultiplied)
        self.pristine.setDevicePixelRatio(ratio)
        self.dpr = ratio
        # everything below this line is in logical pixels; only the two raw
        # pixel pokes in restore_circle() convert back to device space
        self.field = QRectF(0, 0,
                            self.pristine.width() / ratio,
                            self.pristine.height() / ratio)
        self.canvas = QPixmap.fromImage(self.pristine)
        self.canvas.setDevicePixelRatio(ratio)

        self.particles: list = []
        self.effects: list = []
        self.termites: list = []

        self.cursor = QPointF(self.field.width() / 2, self.field.height() / 2)
        self.cursor_inside = not windowed
        self.pressed = False
        self._last_pos = QPointF(self.cursor)

        self.shake_amount = 0.0
        self.shake_offset = QPoint(0, 0)
        self.hint_time = HINT_SECONDS
        self.hint_text = DEFAULT_HINT

        self.toolbox = Toolbox(session.arsenal, 56, 56)
        self._wash_masks: dict[tuple[int, int], QImage] = {}
        self._dirty = QRegion()
        self._overlay_prev = QRegion()
        self._full = False

        self.setWindowTitle("Desktop Destroyer")
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setCursor(Qt.BlankCursor)

        if windowed:
            self.resize(self.field.size().toSize())
        else:
            if screen is not None:
                self.setScreen(screen)
                self.setGeometry(screen.geometry())
            self.setWindowFlag(Qt.FramelessWindowHint, True)
            self.setWindowState(Qt.WindowFullScreen)

        self.clock = QElapsedTimer()
        self.clock.start()
        self._last_tick = 0
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

    # -- surface protocol used by the weapons -----------------------------

    @property
    def sfx(self):
        return self.session.sfx

    @property
    def weapon(self):
        return self.session.current

    @property
    def diagonal(self) -> float:
        return math.hypot(self.field.width(), self.field.height())

    def rect_f(self) -> QRectF:
        return QRectF(self.field)

    @contextmanager
    def painter(self):
        p = QPainter(self.canvas)
        p.setRenderHint(QPainter.Antialiasing, True)
        try:
            yield p
        finally:
            p.end()

    def add(self, particle) -> None:
        if len(self.particles) < MAX_PARTICLES:
            self.particles.append(particle)

    def mark(self, rect: QRectF | QRect) -> None:
        if self._full:
            return
        aligned = rect.toAlignedRect() if isinstance(rect, QRectF) else rect
        self._dirty += aligned.intersected(self.rect())

    def mark_all(self) -> None:
        self._full = True

    def shake(self, amount: float) -> None:
        self.shake_amount = max(self.shake_amount, amount)

    def restore_circle(self, x: float, y: float, radius: float, strength: float) -> None:
        """Blit the untouched screenshot back through a soft round mask."""
        d = self.dpr
        r = max(1, round(radius * d))
        full = QRect(round(x * d) - r, round(y * d) - r, r * 2, r * 2)
        clipped = full.intersected(QRect(0, 0, self.pristine.width(),
                                         self.pristine.height()))
        if clipped.isEmpty():
            return
        piece = self.pristine.copy(clipped)
        piece.setDevicePixelRatio(1.0)  # composite the mask in device pixels
        mp = QPainter(piece)
        mp.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        mp.drawImage(clipped.topLeft() - full.topLeft(), self._wash_mask(r, strength))
        mp.end()
        piece.setDevicePixelRatio(d)

        target = QRectF(clipped.x() / d, clipped.y() / d,
                        clipped.width() / d, clipped.height() / d)
        with self.painter() as p:
            p.drawImage(target.topLeft(), piece)
        self.mark(target)

    def _wash_mask(self, radius: int, strength: float) -> QImage:
        key = (radius, int(strength * 100))
        cached = self._wash_masks.get(key)
        if cached is not None:
            return cached
        from PySide6.QtGui import QRadialGradient

        size = radius * 2
        mask = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
        mask.fill(Qt.transparent)
        alpha = int(255 * min(1.0, max(0.0, strength)))
        gradient = QRadialGradient(radius, radius, radius)
        gradient.setColorAt(0.0, QColor(255, 255, 255, alpha))
        gradient.setColorAt(0.55, QColor(255, 255, 255, int(alpha * 0.75)))
        gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
        p = QPainter(mask)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(gradient)
        p.drawEllipse(0, 0, size, size)
        p.end()
        self._wash_masks[key] = mask
        return mask

    # -- housekeeping ------------------------------------------------------

    def toast(self, text: str, seconds: float = 2.6) -> None:
        """Flash a short message in the banner slot at the top."""
        self.hint_text = text
        self.hint_time = seconds
        self.mark(self._hint_rect())

    def repair_all(self) -> None:
        self.canvas = QPixmap.fromImage(self.pristine)
        self.canvas.setDevicePixelRatio(self.dpr)
        self.particles.clear()
        self.effects.clear()
        self.termites.clear()
        self.mark_all()

    def save_shot(self) -> str | None:
        pictures = os.environ.get("XDG_PICTURES_DIR") or str(Path.home() / "Pictures")
        target = Path(pictures)
        if not target.is_dir():
            target = Path.home() / "Bilder"
        if not target.is_dir():
            target = Path.home()
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = target / f"desktop-destroyer-{stamp}.png"
        return str(path) if self.canvas.save(str(path)) else None

    # -- the loop ----------------------------------------------------------

    def _tick(self) -> None:
        now = self.clock.elapsed()
        dt = min(0.05, max(0.0005, (now - self._last_tick) / 1000.0))
        self._last_tick = now

        weapon = self.weapon
        weapon.tick(self, dt)

        self.effects[:] = [e for e in self.effects if e.step(self, dt)]
        self.particles[:] = [p for p in self.particles if p.step(dt)]
        self._step_termites(dt)

        if self.shake_amount > 0.01:
            self.shake_amount *= math.pow(0.0016, dt)
            if self.shake_amount < 0.35:
                self.shake_amount = 0.0
                self.shake_offset = QPoint(0, 0)
            else:
                self.shake_offset = QPoint(
                    int(rng.uniform(-self.shake_amount, self.shake_amount)),
                    int(rng.uniform(-self.shake_amount, self.shake_amount)),
                )
            self.mark_all()

        if self.hint_time > 0.0:
            self.hint_time -= dt
            self.mark(self._hint_rect())

        overlay = self._overlay_region()
        self._dirty += overlay
        self._dirty += self._overlay_prev
        self._overlay_prev = overlay

        if self.toolbox.visible and self.toolbox.dragging:
            self.mark(self.toolbox.rect().adjusted(-8, -8, 12, 14))

        if self._full:
            self._full = False
            self._dirty = QRegion()
            self.update()
        elif not self._dirty.isEmpty():
            self.update(self._dirty)
            self._dirty = QRegion()

    def _step_termites(self, dt: float) -> None:
        if not self.termites:
            return
        bites: list[QPointF] = []
        alive = []
        for termite in self.termites:
            self.mark(termite.bounds_rect())
            spot = termite.step(dt)
            if spot is not None:
                bites.append(spot)
            self.mark(termite.bounds_rect())
            if termite.alive:
                alive.append(termite)
        self.termites = alive

        if bites:
            with self.painter() as p:
                p.setPen(Qt.NoPen)
                for spot in bites:
                    radius = rng.uniform(3.0, 6.4)
                    p.setBrush(VOID)
                    p.drawPath(bite_path(spot.x(), spot.y(), radius))
                    if rng.random() < 0.22:  # a rim on every bite reads as beads
                        p.setPen(QPen(QColor(255, 255, 255, 34), 1.0))
                        p.setBrush(Qt.NoBrush)
                        p.drawPath(bite_path(spot.x(), spot.y(), radius * 1.2))
                        p.setPen(Qt.NoPen)
                        p.setBrush(VOID)

    def _overlay_region(self) -> QRegion:
        region = QRegion()
        for particle in self.particles:
            region += particle.bounds().toAlignedRect()
        for termite in self.termites:
            region += termite.bounds_rect().toAlignedRect()
        if self.cursor_inside:
            region += self.weapon.cursor_bounds(self.cursor).toAlignedRect()
        bounds = self.weapon.overlay_bounds(self)
        if bounds is not None:
            region += bounds.toAlignedRect()
        return region.intersected(QRegion(self.rect()))

    # -- painting ----------------------------------------------------------

    def _hint_rect(self) -> QRectF:
        return QRectF(self.width() / 2 - 460, 18, 920, 54)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        if self.shake_offset.isNull():
            p.drawPixmap(0, 0, self.canvas)
        else:
            p.fillRect(self.rect(), QColor(8, 8, 10))
            p.drawPixmap(self.shake_offset, self.canvas)

        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        self.weapon.draw_overlay(p, self)
        draw_particles(p, self.particles)
        for termite in self.termites:
            termite.draw(p)

        if self.cursor_inside:
            self.weapon.draw_cursor(p, self.cursor, self.pressed)

        self.toolbox.draw(p, self.session.index)

        if self.hint_time > 0.0:
            self._draw_hint(p)
        p.end()

    def _draw_hint(self, p: QPainter) -> None:
        fade = min(1.0, self.hint_time / 1.6)
        box = self._hint_rect()
        p.save()
        p.setOpacity(fade)
        path = QPainterPath()
        path.addRoundedRect(box, 12, 12)
        p.setPen(QPen(QColor(140, 110, 240, 180), 1.5))
        p.fillPath(path, QColor(20, 12, 44, 205))
        p.drawPath(path)
        font = QFont("DejaVu Sans", 12)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor("#EDE6FF"))
        p.drawText(box, Qt.AlignCenter, self.hint_text)
        p.restore()

    # -- input -------------------------------------------------------------

    def _point(self, event) -> QPointF:
        return event.position() if hasattr(event, "position") else QPointF(event.pos())

    def mousePressEvent(self, event) -> None:
        point = self._point(event)
        self.cursor = point
        self.cursor_inside = True

        if event.button() == Qt.RightButton:
            self.session.toggle_toolbox()
            return
        if event.button() != Qt.LeftButton:
            return

        hit = self.toolbox.press(point)
        if hit == "close":
            self.session.toggle_toolbox()
            return
        if hit == "drag" or hit == "panel":
            self.mark(self.toolbox.rect().adjusted(-8, -8, 12, 14))
            return
        if isinstance(hit, int):
            self.session.select(hit)
            return

        self.pressed = True
        self._last_pos = point
        self.weapon.press(self, point)

    def mouseMoveEvent(self, event) -> None:
        point = self._point(event)
        self.cursor = point
        self.cursor_inside = True

        if self.toolbox.dragging:
            if self.toolbox.drag(point, self.rect()):
                self.mark_all()
            return

        if self.pressed:
            dt = 1 / 60.0
            self.weapon.drag(self, point, self._last_pos, dt)
            self._last_pos = point

    def mouseReleaseEvent(self, event) -> None:
        if self.toolbox.dragging:
            self.toolbox.release()
            return
        if event.button() == Qt.LeftButton and self.pressed:
            self.pressed = False
            self.weapon.release(self)

    def wheelEvent(self, event) -> None:
        step = 1 if event.angleDelta().y() < 0 else -1
        self.session.select((self.session.index + step) % len(self.session.arsenal))

    def enterEvent(self, event) -> None:
        self.cursor_inside = True

    def leaveEvent(self, event) -> None:
        self.cursor_inside = False
        if self.pressed:
            self.pressed = False
            self.weapon.release(self)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        text = event.text()
        if key in (Qt.Key_Escape, Qt.Key_Q):
            self.session.quit()
        elif text.isdigit() and text != "0":
            self.session.select(int(text) - 1)
        elif key == Qt.Key_Tab or key == Qt.Key_F1:
            self.session.toggle_toolbox()
        elif key == Qt.Key_R:
            self.session.repair()
        elif key == Qt.Key_S:
            self.session.save()
        elif key == Qt.Key_M:
            self.session.toggle_sound()
        elif key == Qt.Key_Space:
            self.session.select((self.session.index + 1) % len(self.session.arsenal))
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self.timer.stop()
        super().closeEvent(event)
