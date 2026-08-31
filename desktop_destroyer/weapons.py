"""The nine tools of destruction.

Every weapon works against a *surface* (a DestroyerWindow) and speaks a small
protocol:

    press(surf, pos)          mouse went down
    drag(surf, pos, prev, dt) mouse moved while down
    release(surf)             mouse came up
    tick(surf, dt)            once per frame, held or not
    draw_cursor(p, pos, held) the tool that follows the mouse
    draw_overlay(p, surf)     transient extras drawn above the canvas

Damage is painted straight onto ``surf.canvas`` and is permanent -- only the
washing gun can undo it, by blitting the pristine screenshot back.
"""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)

from . import icons
from .fx import Particle, Termite

rng = random.Random()

VOID = QColor(14, 13, 16)  # what you see once a hole goes all the way through


def _pad(rect: QRectF, amount: float) -> QRectF:
    return rect.adjusted(-amount, -amount, amount, amount)


def _blob(x: float, y: float, radius: float, wobble: float = 0.35,
          points: int = 11) -> QPainterPath:
    """An irregular closed splodge -- nothing in here should look like a circle."""
    path = QPainterPath()
    coords = []
    for i in range(points):
        angle = math.tau * i / points
        r = radius * (1.0 + rng.uniform(-wobble, wobble))
        coords.append(QPointF(x + math.cos(angle) * r, y + math.sin(angle) * r))
    path.moveTo(coords[0])
    for i in range(points):
        current, following = coords[i], coords[(i + 1) % points]
        mid = QPointF((current.x() + following.x()) / 2, (current.y() + following.y()) / 2)
        path.quadTo(current, mid)
    path.closeSubpath()
    return path


def _crack(p: QPainter, x: float, y: float, angle: float, length: float,
           width: float, depth: int = 1) -> QRectF:
    """A jagged fracture line with a lit edge, optionally forking."""
    segments = max(3, int(length / 10))
    step = length / segments
    path = QPainterPath(QPointF(x, y))
    cx, cy, heading = x, y, angle
    branch_from = None
    for i in range(segments):
        heading += rng.uniform(-0.42, 0.42)
        cx += math.cos(heading) * step
        cy += math.sin(heading) * step
        path.lineTo(cx, cy)
        if depth > 0 and i == segments // 2:
            branch_from = (cx, cy, heading)

    # an open path drawn with a brush set gets *filled*, which turns every
    # fracture into a grey feather -- stroke it and nothing else
    p.save()
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(12, 11, 13, 235), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPath(path)
    p.setPen(QPen(QColor(255, 255, 255, 70), max(1.0, width * 0.45),
                  Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.translate(0.9, 0.9)
    p.drawPath(path)
    p.restore()

    rect = path.boundingRect()
    if branch_from:
        bx, by, bh = branch_from
        rect = rect.united(
            _crack(p, bx, by, bh + rng.choice((-1, 1)) * rng.uniform(0.5, 1.1),
                   length * rng.uniform(0.35, 0.6), max(1.0, width * 0.65), depth - 1)
        )
    return rect


# ==========================================================================


class Weapon:
    key = ""
    label = ""
    number = 0
    anchor = (0.5, 0.5)     # point of the 100x100 icon that sits on the cursor
    cursor_size = 104
    loop_sound: str | None = None
    repeat = 0.0            # seconds between shots while held; 0 = one shot per click

    def __init__(self) -> None:
        self._cooldown = 0.0
        self.held = False

    # -- lifecycle ---------------------------------------------------------

    def press(self, surf, pos: QPointF) -> None:
        self.held = True
        self._cooldown = 0.0
        if self.loop_sound:
            surf.sfx.loop(self.loop_sound, True)
        self.fire(surf, pos, pos)

    def drag(self, surf, pos: QPointF, prev: QPointF, dt: float) -> None:
        if not self.repeat:
            self.fire(surf, pos, prev)

    def release(self, surf) -> None:
        self.held = False
        if self.loop_sound:
            surf.sfx.loop(self.loop_sound, False)

    def tick(self, surf, dt: float) -> None:
        # `held` is per weapon but `pressed` is per screen -- without the second
        # check a held trigger would also fire on every other monitor
        if self.held and self.repeat and surf.pressed:
            self._cooldown -= dt
            while self._cooldown <= 0.0:
                self._cooldown += self.repeat
                self.fire(surf, surf.cursor, surf.cursor)

    def deactivate(self, surf) -> None:
        """Switched away from, or the window lost focus."""
        if self.held:
            self.release(surf)

    # -- what it actually does --------------------------------------------

    def fire(self, surf, pos: QPointF, prev: QPointF) -> None:
        raise NotImplementedError

    # -- looks -------------------------------------------------------------

    def draw_cursor(self, painter: QPainter, pos: QPointF, held: bool) -> None:
        size = self.cursor_size
        pixmap = icons.render(self.key, size, shadow=True)
        painter.drawPixmap(
            QPointF(pos.x() - self.anchor[0] * size, pos.y() - self.anchor[1] * size),
            pixmap,
        )

    def cursor_bounds(self, pos: QPointF) -> QRectF:
        size = self.cursor_size
        return QRectF(pos.x() - self.anchor[0] * size - 8,
                      pos.y() - self.anchor[1] * size - 8,
                      size + 16, size + 16)

    def draw_overlay(self, painter: QPainter, surf) -> None:
        """Transient beams and the like, drawn under the cursor tool."""

    def overlay_bounds(self, surf) -> QRectF | None:
        return None


# --------------------------------------------------------------------------
# 1 -- Hammer
# --------------------------------------------------------------------------


class Hammer(Weapon):
    key, label, number = "hammer", "Hammer", 1
    anchor = (0.67, 0.37)

    def drag(self, surf, pos, prev, dt):
        pass  # one dent per click, like the original

    def fire(self, surf, pos, prev):
        x, y = pos.x(), pos.y()
        radius = rng.uniform(15, 23)
        dirty = QRectF(x - radius, y - radius, radius * 2, radius * 2)

        with surf.painter() as p:
            crater = _blob(x, y, radius, 0.42)
            p.fillPath(crater, VOID)
            p.setPen(QPen(QColor(255, 255, 255, 55), 1.6))
            p.setBrush(Qt.NoBrush)
            p.drawPath(crater)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 90))
            p.drawPath(_blob(x + 2, y + 2, radius * 0.55, 0.5))

            for _ in range(rng.randint(9, 14)):
                angle = rng.uniform(0, math.tau)
                start = QPointF(x + math.cos(angle) * radius * 0.8,
                                y + math.sin(angle) * radius * 0.8)
                dirty = dirty.united(
                    _crack(p, start.x(), start.y(), angle,
                           rng.uniform(38, 115), rng.uniform(1.4, 2.8))
                )

        for _ in range(22):
            angle = rng.uniform(0, math.tau)
            speed = rng.uniform(90, 380)
            surf.add(Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed - 130,
                              rng.uniform(0.4, 0.9), rng.uniform(1.6, 4.0),
                              QColor(200, 198, 196), "chip"))
        for _ in range(10):
            angle = rng.uniform(0, math.tau)
            surf.add(Particle(x, y, math.cos(angle) * rng.uniform(20, 90),
                              math.sin(angle) * rng.uniform(20, 90) - 40,
                              rng.uniform(0.5, 1.0), rng.uniform(4, 9),
                              QColor(190, 190, 190), "smoke", gravity=-0.05))

        surf.shake(rng.uniform(7, 12))
        surf.sfx.play("hammer", 0.75)
        surf.mark(_pad(dirty, 8))


# --------------------------------------------------------------------------
# 2 -- Chain-saw
# --------------------------------------------------------------------------


class ChainSaw(Weapon):
    key, label, number = "chainsaw", "Chain-saw", 2
    anchor = (0.05, 0.58)
    loop_sound = "saw"

    def __init__(self):
        super().__init__()
        self.phase = 0.0
        self._kerf = 0.0
        self._carry = None   # kerf half-widths where the last stroke ended

    def press(self, surf, pos):
        self._carry = None
        super().press(surf, pos)

    def tick(self, surf, dt):
        self.phase += dt * (34.0 if self.held else 9.0)

    def fire(self, surf, pos, prev):
        ax, ay = prev.x(), prev.y()
        bx, by = pos.x(), pos.y()
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        if length < 0.6:
            dx, dy, length = 1.0, 0.0, 1.0
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux

        steps = max(3, int(length / 7) + 2)
        top, bottom, halves = [], [], []
        for i in range(steps + 1):
            t = i / steps
            px, py = ax + dx * t, ay + dy * t
            if i == 0 and self._carry is not None:
                # pick the width up exactly where the previous segment left off,
                # otherwise the stroke turns into a chain of separate links
                half_top, half_bottom = self._carry
            else:
                self._kerf += 0.55
                wobble = 1.9 * math.sin(self._kerf) + 1.0 * math.sin(self._kerf * 2.7)
                half_top = 6.4 + wobble + rng.uniform(-0.7, 0.7)
                half_bottom = 6.4 - wobble * 0.6 + rng.uniform(-0.7, 0.7)
            halves.append((half_top, half_bottom))
            top.append(QPointF(px + nx * half_top, py + ny * half_top))
            bottom.append(QPointF(px - nx * half_bottom, py - ny * half_bottom))
        self._carry = halves[-1]

        cut = QPainterPath()
        cut.moveTo(top[0])
        for point in top[1:]:
            cut.lineTo(point)
        for point in reversed(bottom):
            cut.lineTo(point)
        cut.closeSubpath()

        with surf.painter() as p:
            p.fillPath(cut, VOID)
            # light only the two long edges -- stroking the closed quad would
            # draw a seam straight across the cut at every segment boundary
            p.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
            p.setBrush(Qt.NoBrush)
            for side in (top, bottom):
                edge = QPainterPath(side[0])
                for point in side[1:]:
                    edge.lineTo(point)
                p.drawPath(edge)
            # the odd splinter torn out of the edge
            p.setPen(QPen(QColor(26, 22, 20, 190), 1.1))
            for i in range(0, steps, 3):
                if rng.random() > 0.55:
                    continue
                t = i / steps
                px, py = ax + dx * t, ay + dy * t
                side = rng.choice((1, -1))
                tooth = rng.uniform(2.5, 7.5)
                p.drawLine(QPointF(px + nx * side * 5.5, py + ny * side * 5.5),
                           QPointF(px + nx * side * (5.5 + tooth) + ux * rng.uniform(-3, 3),
                                   py + ny * side * (5.5 + tooth) + uy * rng.uniform(-3, 3)))

        for _ in range(int(3 + length * 0.35)):
            side = rng.choice((1, -1))
            speed = rng.uniform(120, 340)
            surf.add(Particle(bx, by,
                              nx * side * speed + ux * rng.uniform(-60, 60),
                              ny * side * speed + uy * rng.uniform(-60, 60) - 60,
                              rng.uniform(0.30, 0.75), rng.uniform(1.2, 2.8),
                              QColor(226, 200, 150), "chip", drag=2.0))

        dirty = cut.boundingRect()
        surf.mark(_pad(dirty, 16))

    def draw_cursor(self, painter, pos, held):
        if held:
            painter.save()
            painter.translate(rng.uniform(-1.6, 1.6), rng.uniform(-1.6, 1.6))
            super().draw_cursor(painter, pos, held)
            painter.restore()
            # the chain, whipping round the bar tip
            painter.save()
            painter.translate(pos)
            painter.setPen(QPen(QColor(70, 70, 74, 200), 2.0))
            for i in range(6):
                a = self.phase + i * math.tau / 6
                painter.drawLine(QPointF(math.cos(a) * 7, math.sin(a) * 7),
                                 QPointF(math.cos(a) * 11, math.sin(a) * 11))
            painter.restore()
        else:
            super().draw_cursor(painter, pos, held)


# --------------------------------------------------------------------------
# 3 -- Machine gun
# --------------------------------------------------------------------------


class MachineGun(Weapon):
    key, label, number = "machinegun", "Machine gun", 3
    anchor = (1.03, 0.35)
    repeat = 0.075

    def __init__(self):
        super().__init__()
        self.recoil = 0.0
        self.flash = 0.0

    def tick(self, surf, dt):
        super().tick(surf, dt)
        self.recoil = max(0.0, self.recoil - dt * 26)
        self.flash = max(0.0, self.flash - dt * 22)

    def fire(self, surf, pos, prev):
        x = pos.x() + rng.uniform(-11, 11)
        y = pos.y() + rng.uniform(-11, 11)
        radius = rng.uniform(3.6, 6.0)
        dirty = QRectF(x - 26, y - 26, 52, 52)

        with surf.painter() as p:
            halo = QRadialGradient(QPointF(x, y), radius * 4.2)
            halo.setColorAt(0.0, QColor(255, 255, 255, 55))
            halo.setColorAt(0.45, QColor(180, 175, 170, 40))
            halo.setColorAt(1.0, QColor(150, 145, 140, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(halo)
            p.drawEllipse(QPointF(x, y), radius * 4.2, radius * 4.2)

            p.setBrush(QColor(56, 52, 50, 220))
            p.drawPath(_blob(x, y, radius * 1.7, 0.30))
            p.fillPath(_blob(x, y, radius, 0.25), VOID)
            p.setPen(QPen(QColor(255, 255, 255, 60), 1.2))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(x, y), radius * 1.25, radius * 1.25)

            for _ in range(rng.randint(4, 7)):
                angle = rng.uniform(0, math.tau)
                dirty = dirty.united(
                    _crack(p, x + math.cos(angle) * radius, y + math.sin(angle) * radius,
                           angle, rng.uniform(10, 26), 1.3, depth=0)
                )

        for _ in range(6):
            angle = rng.uniform(0, math.tau)
            speed = rng.uniform(60, 240)
            surf.add(Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed - 80,
                              rng.uniform(0.25, 0.55), rng.uniform(1.0, 2.4),
                              QColor(210, 206, 200), "chip"))
        surf.add(Particle(x, y, rng.uniform(-25, 25), rng.uniform(-45, -15),
                          rng.uniform(0.4, 0.8), rng.uniform(5, 10),
                          QColor(200, 200, 200), "smoke", gravity=-0.08))

        muzzle = surf.cursor
        surf.add(Particle(muzzle.x() - 6, muzzle.y() + 6,
                          rng.uniform(-190, -70), rng.uniform(-210, -110),
                          rng.uniform(0.5, 0.9), rng.uniform(2.0, 3.0),
                          QColor(214, 170, 62), "casing"))

        self.recoil = 1.0
        self.flash = 1.0
        surf.shake(1.6)
        surf.sfx.play("gunshot", 0.45)
        surf.mark(_pad(dirty, 8))

    def draw_cursor(self, painter, pos, held):
        painter.save()
        painter.translate(self.recoil * 7.0, self.recoil * 2.5)
        super().draw_cursor(painter, pos, held)
        painter.restore()
        if self.flash > 0.05:
            painter.save()
            painter.setCompositionMode(QPainter.CompositionMode_Plus)
            radius = 16 + 12 * self.flash
            flare = QRadialGradient(pos, radius)
            flare.setColorAt(0.0, QColor(255, 246, 200, int(220 * self.flash)))
            flare.setColorAt(0.4, QColor(255, 170, 40, int(150 * self.flash)))
            flare.setColorAt(1.0, QColor(255, 120, 0, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(flare)
            painter.drawEllipse(pos, radius, radius)
            painter.restore()

    def cursor_bounds(self, pos):
        return super().cursor_bounds(pos).adjusted(-34, -34, 34, 34)


# --------------------------------------------------------------------------
# 4 -- Flame-thrower
# --------------------------------------------------------------------------


class FlameThrower(Weapon):
    key, label, number = "flamethrower", "Flame-thrower", 4
    anchor = (0.167, 0.094)
    loop_sound = "flame"
    repeat = 1 / 60

    def __init__(self):
        super().__init__()
        self.aim = QPointF(0.82, -0.57)

    def drag(self, surf, pos, prev, dt):
        dx, dy = pos.x() - prev.x(), pos.y() - prev.y()
        length = math.hypot(dx, dy)
        if length > 2.0:
            k = min(1.0, dt * 9.0)
            self.aim = QPointF(self.aim.x() + (dx / length - self.aim.x()) * k,
                               self.aim.y() + (dy / length - self.aim.y()) * k)

    def fire(self, surf, pos, prev):
        x, y = pos.x(), pos.y()
        radius = 46.0

        with surf.painter() as p:
            char = QRadialGradient(QPointF(x, y), radius)
            char.setColorAt(0.0, QColor(22, 13, 8, 62))
            char.setColorAt(0.40, QColor(44, 23, 11, 42))
            char.setColorAt(0.78, QColor(96, 44, 14, 16))
            char.setColorAt(1.0, QColor(120, 58, 18, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(char)
            p.drawEllipse(QPointF(x, y), radius, radius)

            core = QRadialGradient(QPointF(x, y), radius * 0.5)
            core.setColorAt(0.0, QColor(0, 0, 0, 72))
            core.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(core)
            p.drawEllipse(QPointF(x, y), radius * 0.5, radius * 0.5)

            # a ring of embers creeping outward along the burn front
            if rng.random() < 0.7:
                ring = QRadialGradient(QPointF(x, y), radius)
                ring.setColorAt(0.0, QColor(255, 120, 20, 0))
                ring.setColorAt(0.72, QColor(255, 120, 20, 0))
                ring.setColorAt(0.88, QColor(255, 146, 34, 26))
                ring.setColorAt(1.0, QColor(255, 90, 10, 0))
                p.setBrush(ring)
                p.drawEllipse(QPointF(x, y), radius, radius)

            if rng.random() < 0.45:  # blistered paint, glowing at the rim
                bx = x + rng.uniform(-radius, radius) * 0.7
                by = y + rng.uniform(-radius, radius) * 0.7
                size = rng.uniform(2.5, 7.0)
                p.setBrush(QColor(10, 8, 8, 200))
                p.drawPath(_blob(bx, by, size, 0.5, 8))
                p.setPen(QPen(QColor(255, rng.randint(90, 170), 20,
                                     rng.randint(70, 150)), 1.3))
                p.setBrush(Qt.NoBrush)
                p.drawPath(_blob(bx, by, size * 1.25, 0.5, 8))

        ax, ay = self.aim.x(), self.aim.y()
        for _ in range(7):
            spread = rng.uniform(-0.42, 0.42)
            cos_s, sin_s = math.cos(spread), math.sin(spread)
            jx = ax * cos_s - ay * sin_s
            jy = ax * sin_s + ay * cos_s
            speed = rng.uniform(150, 470)
            surf.add(Particle(x + rng.uniform(-7, 7), y + rng.uniform(-7, 7),
                              jx * speed, jy * speed,
                              rng.uniform(0.35, 0.8), rng.uniform(7, 15),
                              None, "flame", gravity=-0.30, drag=1.5))
        if rng.random() < 0.28:
            surf.add(Particle(x + rng.uniform(-12, 12), y,
                              rng.uniform(-40, 40), rng.uniform(-130, -60),
                              rng.uniform(0.8, 1.5), rng.uniform(7, 14),
                              None, "smoke", gravity=-0.10, drag=0.6))

        surf.mark(QRectF(x - radius - 6, y - radius - 6, radius * 2 + 12, radius * 2 + 12))


# --------------------------------------------------------------------------
# 5 -- Colour-thrower
# --------------------------------------------------------------------------


class Drip:
    """A run of wet paint crawling down the screen, painted as it goes."""

    def __init__(self, x, y, width, color):
        self.x, self.y = x, y
        self.width = width
        self.color = color
        self.speed = rng.uniform(26, 90)
        self.remaining = rng.uniform(40, 260)

    def step(self, surf, dt) -> bool:
        advance = min(self.speed * dt, self.remaining)
        if advance <= 0.0 or self.y > surf.height():
            return False
        with surf.painter() as p:
            p.setPen(Qt.NoPen)
            p.setBrush(self.color)
            p.drawRoundedRect(
                QRectF(self.x - self.width / 2, self.y, self.width, advance + 1.5),
                self.width / 2, self.width / 2)
        surf.mark(QRectF(self.x - self.width, self.y - 1, self.width * 2, advance + 6))
        self.y += advance
        self.remaining -= advance
        self.width = max(1.2, self.width - dt * 1.4)
        self.speed *= 1.0 - 0.25 * dt
        return self.remaining > 0.0


class ColorThrower(Weapon):
    key, label, number = "colorthrower", "Color-thrower", 5
    anchor = (0.167, 0.094)
    loop_sound = "spray"
    repeat = 1 / 34

    def __init__(self):
        super().__init__()
        self.hue = rng.random()

    def press(self, surf, pos):
        self.hue = rng.random()
        super().press(surf, pos)

    def _ink(self, jitter=0.05) -> QColor:
        return QColor.fromHsvF((self.hue + rng.uniform(-jitter, jitter)) % 1.0,
                               rng.uniform(0.75, 1.0), rng.uniform(0.80, 1.0))

    def fire(self, surf, pos, prev):
        self.hue = (self.hue + 0.004) % 1.0
        x, y = pos.x(), pos.y()
        color = self._ink()
        radius = rng.uniform(11, 24)
        dirty = QRectF(x - 60, y - 60, 120, 120)

        with surf.painter() as p:
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawPath(_blob(x, y, radius, 0.40))
            gloss = QRadialGradient(QPointF(x - radius * 0.3, y - radius * 0.35), radius)
            gloss.setColorAt(0.0, QColor(255, 255, 255, 90))
            gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(gloss)
            p.drawPath(_blob(x, y, radius * 0.9, 0.40))

            for _ in range(rng.randint(4, 9)):
                angle = rng.uniform(0, math.tau)
                distance = rng.uniform(radius, radius * 3.0)
                sx = x + math.cos(angle) * distance
                sy = y + math.sin(angle) * distance
                p.setBrush(self._ink(0.03))
                p.drawPath(_blob(sx, sy, rng.uniform(1.2, 5.0), 0.5, 8))

        if rng.random() < 0.16:
            surf.effects.append(Drip(x + rng.uniform(-radius, radius),
                                     y + radius * 0.7,
                                     rng.uniform(2.5, 6.0), color))
        for _ in range(3):
            angle = rng.uniform(0, math.tau)
            speed = rng.uniform(40, 190)
            surf.add(Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed - 70,
                              rng.uniform(0.25, 0.6), rng.uniform(1.5, 3.5),
                              self._ink(0.04), "spark", drag=1.2))

        surf.mark(dirty)


# --------------------------------------------------------------------------
# 6 -- Phaser
# --------------------------------------------------------------------------


class Phaser(Weapon):
    key, label, number = "phaser", "Phaser", 6
    anchor = (0.20, 0.14)
    repeat = 1 / 14  # the beam is drawn every frame; it only *burns* this often

    def __init__(self):
        super().__init__()
        self.aim = QPointF(0.94, 0.34)
        self.beam: tuple[QPointF, QPointF] | None = None
        self.intensity = 0.0

    def press(self, surf, pos):
        surf.sfx.play("phaser", 0.55)
        super().press(surf, pos)

    def release(self, surf):
        super().release(surf)
        self.beam = None
        surf.mark_all()

    def drag(self, surf, pos, prev, dt):
        dx, dy = pos.x() - prev.x(), pos.y() - prev.y()
        length = math.hypot(dx, dy)
        if length > 2.5:
            k = min(1.0, dt * 7.0)
            self.aim = QPointF(self.aim.x() + (dx / length - self.aim.x()) * k,
                               self.aim.y() + (dy / length - self.aim.y()) * k)

    def tick(self, surf, dt):
        super().tick(surf, dt)
        self.intensity = max(0.0, self.intensity - dt * 3.0)

    def _endpoint(self, surf, origin: QPointF) -> QPointF:
        ax, ay = self.aim.x(), self.aim.y()
        norm = math.hypot(ax, ay) or 1.0
        ax, ay = ax / norm, ay / norm
        far = math.hypot(surf.width(), surf.height()) * 1.2
        return QPointF(origin.x() + ax * far, origin.y() + ay * far)

    def fire(self, surf, pos, prev):
        origin = QPointF(pos)
        end = self._endpoint(surf, origin)
        self.beam = (origin, end)
        self.intensity = 1.0

        with surf.painter() as p:
            p.setPen(QPen(QColor(255, 120, 30, 10), 12, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(origin, end)   # heat haze either side of the cut
            p.setPen(QPen(QColor(46, 22, 12, 34), 6.5, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(origin, end)   # scorched margin
            p.setPen(QPen(QColor(7, 6, 8, 150), 4.0, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(origin, end)   # the slit itself

            # molten craters flicker along the burn
            distance = math.hypot(end.x() - origin.x(), end.y() - origin.y())
            ux = (end.x() - origin.x()) / (distance or 1)
            uy = (end.y() - origin.y()) / (distance or 1)
            for _ in range(3):
                t = rng.uniform(0, min(distance, surf.diagonal))
                cx, cy = origin.x() + ux * t, origin.y() + uy * t
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(6, 5, 6, 190))
                p.drawPath(_blob(cx, cy, rng.uniform(1.6, 4.2), 0.5, 8))
                glow = QRadialGradient(QPointF(cx, cy), 9)
                glow.setColorAt(0.0, QColor(255, 150, 30, 90))
                glow.setColorAt(1.0, QColor(255, 90, 10, 0))
                p.setBrush(glow)
                p.drawEllipse(QPointF(cx, cy), 9, 9)

        for _ in range(3):
            t = rng.uniform(0, 1)
            sx = origin.x() + (end.x() - origin.x()) * t * 0.6
            sy = origin.y() + (end.y() - origin.y()) * t * 0.6
            angle = rng.uniform(0, math.tau)
            speed = rng.uniform(60, 260)
            surf.add(Particle(sx, sy, math.cos(angle) * speed, math.sin(angle) * speed,
                              rng.uniform(0.2, 0.5), rng.uniform(1.2, 2.6),
                              QColor(255, rng.randint(150, 230), 90), "spark", drag=2.5))

        surf.mark_all()

    def draw_overlay(self, painter, surf):
        if not self.beam or self.intensity <= 0.0:
            return
        origin, end = self.beam
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode_Plus)
        flicker = 0.75 + 0.25 * rng.random()
        for width, color in ((17, QColor(120, 30, 200, int(70 * flicker))),
                             (10, QColor(255, 70, 40, int(120 * flicker))),
                             (5, QColor(255, 190, 90, int(190 * flicker))),
                             (2, QColor(255, 255, 245, int(240 * flicker)))):
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(origin, end)
        glow = QRadialGradient(origin, 30)
        glow.setColorAt(0.0, QColor(255, 240, 210, 200))
        glow.setColorAt(0.35, QColor(255, 120, 40, 120))
        glow.setColorAt(1.0, QColor(180, 40, 10, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(origin, 30, 30)
        painter.restore()

    def overlay_bounds(self, surf):
        return QRectF(0, 0, surf.width(), surf.height()) if self.beam else None


# --------------------------------------------------------------------------
# 7 -- Stamp
# --------------------------------------------------------------------------


class Stamp(Weapon):
    key, label, number = "stamp", "Stamp", 7
    anchor = (0.51, 0.90)

    WORDS = ("DESTROYED", "VOID", "KAPUTT", "REJECTED", "TOP SECRET",
             "APPROVED", "PAID", "COPY", "URGENT", "EXPIRED")
    INKS = ("#C61B2E", "#1D4FA8", "#1E7A3C", "#221F26", "#8A2BE2")

    def __init__(self):
        super().__init__()
        self.press_anim = 0.0

    def drag(self, surf, pos, prev, dt):
        pass

    def tick(self, surf, dt):
        self.press_anim = max(0.0, self.press_anim - dt * 5.0)

    def fire(self, surf, pos, prev):
        text = rng.choice(self.WORDS)
        ink = QColor(rng.choice(self.INKS))
        angle = rng.uniform(-19, 19)
        scale = rng.uniform(0.85, 1.25)

        font = QFont("DejaVu Sans", 30)
        font.setBold(True)
        font.setLetterSpacing(QFont.PercentageSpacing, 118)

        width = int(46 + len(text) * 27)
        height = 108
        mark = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        mark.fill(Qt.transparent)
        mp = QPainter(mark)
        mp.setRenderHint(QPainter.Antialiasing)
        mp.setFont(font)
        mp.setPen(QPen(ink, 6))
        mp.setBrush(Qt.NoBrush)
        mp.drawRoundedRect(QRectF(5, 5, width - 10, height - 10), 9, 9)
        mp.drawRoundedRect(QRectF(13, 13, width - 26, height - 26), 5, 5)
        mp.setPen(ink)
        mp.drawText(QRectF(0, 20, width, 48), Qt.AlignCenter, text)
        small = QFont("DejaVu Sans", 11)
        small.setBold(True)
        small.setLetterSpacing(QFont.PercentageSpacing, 190)
        mp.setFont(small)
        mp.drawText(QRectF(0, height - 34, width, 20), Qt.AlignCenter,
                    "* * * * * * *")
        # grungy ink coverage -- a real rubber stamp never prints solid
        mp.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        mp.setPen(Qt.NoPen)
        for _ in range(320):
            gx, gy = rng.uniform(0, width), rng.uniform(0, height)
            mp.setBrush(QColor(0, 0, 0, rng.randint(60, 235)))
            mp.drawEllipse(QPointF(gx, gy), rng.uniform(0.8, 4.2), rng.uniform(0.8, 3.4))
        mp.end()

        with surf.painter() as p:
            p.save()
            p.translate(pos)
            p.rotate(angle)
            p.scale(scale, scale)
            p.setOpacity(0.82)
            p.drawImage(QPointF(-width / 2, -height / 2), mark)
            p.restore()

        reach = (width + height) * scale
        self.press_anim = 1.0
        surf.shake(3.0)
        surf.sfx.play("stamp", 0.7)
        surf.mark(QRectF(pos.x() - reach / 2, pos.y() - reach / 2, reach, reach))

    def draw_cursor(self, painter, pos, held):
        painter.save()
        painter.translate(0, self.press_anim * 9.0)
        super().draw_cursor(painter, pos, held)
        painter.restore()


# --------------------------------------------------------------------------
# 8 -- Termites
# --------------------------------------------------------------------------


class Termites(Weapon):
    key, label, number = "termites", "Termites", 8
    anchor = (0.51, 0.80)
    MAX = 160

    def drag(self, surf, pos, prev, dt):
        pass

    def fire(self, surf, pos, prev):
        room = self.MAX - len(surf.termites)
        if room <= 0:
            return
        for _ in range(min(room, rng.randint(9, 15))):
            surf.termites.append(
                Termite(pos.x() + rng.uniform(-18, 18),
                        pos.y() + rng.uniform(-18, 18),
                        surf.rect_f())
            )
        surf.sfx.play("chomp", 0.5)
        surf.mark(QRectF(pos.x() - 40, pos.y() - 40, 80, 80))


# --------------------------------------------------------------------------
# 9 -- Washing (the undo button)
# --------------------------------------------------------------------------


class Washing(Weapon):
    key, label, number = "washing", "Washing", 9
    anchor = (0.87, 0.30)
    loop_sound = "water"
    repeat = 1 / 50
    RADIUS = 52

    def fire(self, surf, pos, prev):
        dx, dy = pos.x() - prev.x(), pos.y() - prev.y()
        distance = math.hypot(dx, dy)
        steps = max(1, int(distance / (self.RADIUS * 0.34)))
        for i in range(steps):
            t = (i + 1) / steps
            surf.restore_circle(prev.x() + dx * t, prev.y() + dy * t, self.RADIUS, 0.55)

        x, y = pos.x(), pos.y()
        for _ in range(2):
            surf.add(Particle(x + rng.uniform(-26, 26), y + rng.uniform(-26, 26),
                              rng.uniform(-70, 70), rng.uniform(-150, -40),
                              rng.uniform(0.8, 1.8), rng.uniform(3, 11),
                              QColor(255, 255, 255), "bubble",
                              gravity=-0.16, drag=0.9))
        if rng.random() < 0.35:
            angle = rng.uniform(0, math.tau)
            surf.add(Particle(x, y, math.cos(angle) * rng.uniform(60, 220),
                              math.sin(angle) * rng.uniform(60, 220) - 60,
                              rng.uniform(0.25, 0.6), rng.uniform(1.2, 2.6),
                              QColor(190, 235, 255), "spark", drag=1.6))


# --------------------------------------------------------------------------


def build_arsenal() -> list[Weapon]:
    return [Hammer(), ChainSaw(), MachineGun(), FlameThrower(), ColorThrower(),
            Phaser(), Stamp(), Termites(), Washing()]
