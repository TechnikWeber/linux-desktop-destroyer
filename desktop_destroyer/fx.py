"""Everything that moves on top of the wreckage.

Particles are transient -- they live in an overlay that is repainted every
frame.  Termites are transient too, but they chew permanent holes as they go.
"""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRadialGradient

rng = random.Random()

GRAVITY = 900.0  # px/s^2


class Particle:
    """One short-lived speck: flame, spark, sawdust, paint droplet or bubble."""

    __slots__ = ("x", "y", "vx", "vy", "life", "age", "size", "color", "kind", "spin",
                 "angle", "drag", "gravity")

    def __init__(self, x, y, vx, vy, life, size, color, kind="spark",
                 gravity=1.0, drag=0.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life, self.age = life, 0.0
        self.size = size
        self.color = color
        self.kind = kind
        self.gravity = gravity
        self.drag = drag
        self.spin = rng.uniform(-14, 14)
        self.angle = rng.uniform(0, math.tau)

    @property
    def t(self) -> float:
        """0 at birth, 1 at death."""
        return min(1.0, self.age / self.life)

    def step(self, dt: float) -> bool:
        self.age += dt
        if self.age >= self.life:
            return False
        if self.drag:
            damp = max(0.0, 1.0 - self.drag * dt)
            self.vx *= damp
            self.vy *= damp
        self.vy += GRAVITY * self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.spin * dt
        return True

    def bounds(self) -> QRectF:
        r = self.size * (3.2 if self.kind == "flame" else 1.8) + 3
        return QRectF(self.x - r, self.y - r, 2 * r, 2 * r)


# --------------------------------------------------------------------------
# particle painters
# --------------------------------------------------------------------------

_FLAME_RAMP = (
    (0.00, QColor(255, 255, 226)),
    (0.18, QColor(255, 232, 120)),
    (0.42, QColor(255, 158, 32)),
    (0.68, QColor(226, 68, 16)),
    (0.86, QColor(96, 40, 36)),
    (1.00, QColor(58, 54, 54)),
)


def _ramp(t: float) -> QColor:
    previous = _FLAME_RAMP[0]
    for stop in _FLAME_RAMP:
        if t <= stop[0]:
            span = max(1e-6, stop[0] - previous[0])
            k = (t - previous[0]) / span
            a, b = previous[1], stop[1]
            return QColor(
                int(a.red() + (b.red() - a.red()) * k),
                int(a.green() + (b.green() - a.green()) * k),
                int(a.blue() + (b.blue() - a.blue()) * k),
            )
        previous = stop
    return _FLAME_RAMP[-1][1]


def draw_particles(painter: QPainter, particles) -> None:
    painter.save()
    painter.setPen(Qt.NoPen)
    for p in particles:
        t = p.t
        if p.kind == "flame":
            color = _ramp(t)
            radius = p.size * (0.5 + 2.4 * t)
            alpha = int(235 * (1.0 - t) ** 0.7)
            glow = QRadialGradient(QPointF(p.x, p.y), radius)
            glow.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), alpha))
            glow.setColorAt(0.55, QColor(color.red(), color.green(), color.blue(),
                                         int(alpha * 0.45)))
            glow.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.setBrush(glow)
            painter.drawEllipse(QPointF(p.x, p.y), radius, radius)
        elif p.kind == "smoke":
            radius = p.size * (1.0 + 2.6 * t)
            alpha = int(70 * math.sin(math.pi * min(1.0, t * 1.15)))
            painter.setBrush(QColor(120, 116, 112, max(0, alpha)))
            painter.drawEllipse(QPointF(p.x, p.y), radius, radius)
        elif p.kind == "bubble":
            radius = p.size * (1.0 + 0.5 * t)
            alpha = int(190 * (1.0 - t))
            sheen = QRadialGradient(QPointF(p.x - radius * 0.3, p.y - radius * 0.3), radius * 1.4)
            sheen.setColorAt(0.0, QColor(255, 255, 255, alpha))
            sheen.setColorAt(0.45, QColor(200, 240, 255, alpha // 4))
            sheen.setColorAt(1.0, QColor(150, 220, 255, 0))
            painter.setBrush(sheen)
            painter.drawEllipse(QPointF(p.x, p.y), radius, radius)
            painter.setPen(QPen(QColor(255, 255, 255, alpha // 2), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(p.x, p.y), radius, radius)
            painter.setPen(Qt.NoPen)
        elif p.kind == "chip":
            color = QColor(p.color)
            color.setAlpha(int(255 * (1.0 - t)))
            painter.setBrush(color)
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(math.degrees(p.angle))
            painter.drawRect(QRectF(-p.size, -p.size * 0.6, p.size * 2, p.size * 1.2))
            painter.restore()
        elif p.kind == "casing":
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(math.degrees(p.angle))
            painter.setBrush(QColor(214, 170, 62, int(255 * (1.0 - t))))
            painter.drawRoundedRect(QRectF(-p.size, -p.size * 0.4, p.size * 2,
                                           p.size * 0.8), 1, 1)
            painter.restore()
        else:  # spark / droplet
            color = QColor(p.color)
            color.setAlpha(int(255 * (1.0 - t) ** 0.6))
            painter.setBrush(color)
            radius = p.size * (1.0 - 0.4 * t)
            painter.drawEllipse(QPointF(p.x, p.y), radius, radius)
    painter.restore()


# --------------------------------------------------------------------------
# termites
# --------------------------------------------------------------------------


class Termite:
    """Wanders, bites a hole every few frames, dies of old age."""

    BODY = (QColor("#4A2E15"), QColor("#7A3B1E"), QColor("#8E2B1C"), QColor("#2E1D0E"))

    def __init__(self, x: float, y: float, bounds) -> None:
        self.x, self.y = x, y
        self.angle = rng.uniform(0, math.tau)
        self.speed = rng.uniform(19, 54)
        self.size = rng.uniform(0.75, 1.25)
        self.color = rng.choice(self.BODY)
        self.life = rng.uniform(22.0, 40.0)
        self.age = 0.0
        self.bite_timer = rng.uniform(0.0, 0.07)
        self.leg_phase = rng.uniform(0, math.tau)
        self.bounds = bounds

    @property
    def alive(self) -> bool:
        return self.age < self.life

    def radius(self) -> float:
        return 14.0 * self.size

    def bounds_rect(self) -> QRectF:
        r = self.radius()
        return QRectF(self.x - r, self.y - r, 2 * r, 2 * r)

    def step(self, dt: float) -> QPointF | None:
        """Advance; returns the spot to bite this frame, if any."""
        self.age += dt
        self.angle += rng.uniform(-2.6, 2.6) * dt * 4.5
        self.leg_phase += dt * 16.0
        self.x += math.cos(self.angle) * self.speed * dt
        self.y += math.sin(self.angle) * self.speed * dt

        margin = 6.0
        if self.x < margin or self.x > self.bounds.width() - margin:
            self.angle = math.pi - self.angle
            self.x = min(max(self.x, margin), self.bounds.width() - margin)
        if self.y < margin or self.y > self.bounds.height() - margin:
            self.angle = -self.angle
            self.y = min(max(self.y, margin), self.bounds.height() - margin)

        self.bite_timer -= dt
        if self.bite_timer <= 0.0:
            self.bite_timer = rng.uniform(0.028, 0.075)
            nose = self.radius() * 0.42
            return QPointF(self.x + math.cos(self.angle) * nose,
                           self.y + math.sin(self.angle) * nose)
        return None

    def draw(self, painter: QPainter) -> None:
        fade = 1.0
        remaining = self.life - self.age
        if remaining < 2.0:
            fade = max(0.0, remaining / 2.0)
        painter.save()
        painter.translate(self.x, self.y)
        painter.rotate(math.degrees(self.angle))
        painter.scale(self.size, self.size)
        painter.setOpacity(fade)

        painter.setPen(QPen(QColor(20, 12, 6, 220), 1.3))
        for i in range(3):
            ox = -3.5 + i * 3.5
            swing = math.sin(self.leg_phase + i * 1.7) * 2.2
            painter.drawLine(QPointF(ox, -2), QPointF(ox - 2 + swing, -6))
            painter.drawLine(QPointF(ox, 2), QPointF(ox - 2 - swing, 6))
        painter.drawLine(QPointF(6, -1.4), QPointF(10, -4))
        painter.drawLine(QPointF(6, 1.4), QPointF(10, 4))

        painter.setPen(Qt.NoPen)
        painter.setBrush(self.color)
        painter.drawEllipse(QRectF(-7, -3.2, 10, 6.4))
        painter.setBrush(self.color.lighter(125))
        painter.drawEllipse(QRectF(1.5, -2.8, 6, 5.6))
        painter.setBrush(QColor("#22150A"))
        painter.drawEllipse(QRectF(5, -2.4, 4.4, 4.8))
        painter.restore()


def bite_path(x: float, y: float, radius: float) -> QPainterPath:
    """A ragged, insect-chewed nibble rather than a clean circle."""
    path = QPainterPath()
    steps = 9
    points = []
    for i in range(steps):
        angle = math.tau * i / steps
        r = radius * rng.uniform(0.6, 1.25)
        points.append(QPointF(x + math.cos(angle) * r, y + math.sin(angle) * r))
    path.moveTo(points[0])
    for i in range(steps):
        current = points[i]
        following = points[(i + 1) % steps]
        mid = QPointF((current.x() + following.x()) / 2, (current.y() + following.y()) / 2)
        path.quadTo(current, mid)
    path.closeSubpath()
    return path
