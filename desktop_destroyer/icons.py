"""Every weapon drawn from scratch with QPainter.

No image files anywhere: the toolbox icons and the big tool that follows the
mouse are the same vector art rendered at two different sizes and cached.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)

# Everything below paints inside a 100x100 box; render() scales from there.
BOX = 100.0


def _shade(x1, y1, x2, y2, *stops) -> QLinearGradient:
    gradient = QLinearGradient(x1, y1, x2, y2)
    for offset, color in stops:
        gradient.setColorAt(offset, QColor(color))
    return gradient


def _rounded(p: QPainter, x, y, w, h, r, brush, pen=None) -> None:
    p.setBrush(QBrush(brush))
    p.setPen(QPen(QColor(pen), 1.2) if pen else Qt.NoPen)
    p.drawRoundedRect(QRectF(x, y, w, h), r, r)


def _gloss(p: QPainter, x, y, w, h, r, alpha=90) -> None:
    """A soft white sheen down the left flank -- makes plastic look plastic."""
    p.setPen(Qt.NoPen)
    p.setBrush(_shade(x, y, x + w, y, (0.0, QColor(255, 255, 255, alpha)),
                      (0.45, QColor(255, 255, 255, alpha // 4)),
                      (1.0, QColor(255, 255, 255, 0))))
    p.drawRoundedRect(QRectF(x, y, w, h), r, r)


# --------------------------------------------------------------------------
# the nine tools
# --------------------------------------------------------------------------


def _hammer(p: QPainter) -> None:
    p.translate(48, 54)
    p.rotate(-42)
    # wooden handle
    _rounded(p, -42, -5.5, 60, 11, 5.5,
             _shade(0, -5, 0, 6, (0.0, "#F6CBA4"), (0.5, "#E4A87A"), (1.0, "#B67C50")))
    _rounded(p, -42, -5.5, 12, 11, 5.5, QColor("#C98B5C"))
    # steel head
    head = _shade(16, 0, 38, 0, (0.0, "#8E9AA3"), (0.35, "#D7DEE3"),
                  (0.75, "#9AA6AE"), (1.0, "#6B757D"))
    _rounded(p, 16, -23, 20, 46, 4, head, "#5A646C")
    _rounded(p, 32, -25, 10, 50, 4,
             _shade(0, -25, 0, 25, (0.0, "#EAF0F4"), (1.0, "#A9B4BC")), "#5A646C")
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 110))
    p.drawRoundedRect(QRectF(19, -19, 4, 38), 2, 2)


def _chainsaw(p: QPainter) -> None:
    p.translate(50, 50)
    p.rotate(-10)
    # guide bar
    _rounded(p, -46, -7, 52, 14, 7,
             _shade(0, -7, 0, 7, (0.0, "#E2E7EA"), (0.5, "#A9B2B8"), (1.0, "#79838A")),
             "#5E686E")
    p.setBrush(QColor("#2C3238"))
    p.setPen(Qt.NoPen)
    for i in range(9):
        x = -44 + i * 5.4
        p.drawRect(QRectF(x, -9.5, 3.2, 3.0))
        p.drawRect(QRectF(x + 2.4, 6.5, 3.2, 3.0))
    # red body
    body = _shade(0, -22, 0, 22, (0.0, "#FF4D6E"), (0.45, "#E01340"), (1.0, "#96062A"))
    _rounded(p, 0, -22, 44, 44, 16, body, "#7A0522")
    _gloss(p, 5, -17, 16, 30, 8)
    # rear handle loop, punched clean through
    p.setCompositionMode(QPainter.CompositionMode_Clear)
    p.setBrush(QColor(0, 0, 0, 255))
    p.drawEllipse(QRectF(14, -10, 22, 20))
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    # top handle
    _rounded(p, 2, -28, 26, 9, 4.5, QColor("#3A3F45"))


def _machinegun(p: QPainter) -> None:
    p.translate(50, 52)
    p.rotate(-18)
    dark = _shade(0, -12, 0, 12, (0.0, "#5A626A"), (0.4, "#31373D"), (1.0, "#16191C"))
    # stock and pistol grip
    grip = QPainterPath()
    grip.moveTo(-16, 8)
    grip.lineTo(-4, 8)
    grip.lineTo(-8, 32)
    grip.lineTo(-22, 30)
    grip.closeSubpath()
    p.setPen(QPen(QColor("#101315"), 1.2))
    p.setBrush(QBrush(dark))
    p.drawPath(grip)
    _rounded(p, -44, -8, 30, 16, 5, dark, "#101315")
    # receiver
    _rounded(p, -22, -12, 40, 24, 4, dark, "#101315")
    # magazine
    p.save()
    p.translate(2, 12)
    p.rotate(10)
    _rounded(p, -7, 0, 14, 24, 3, _shade(-7, 0, 7, 0, (0.0, "#4A5158"), (1.0, "#1E2226")),
             "#101315")
    p.restore()
    # vented barrel shroud
    _rounded(p, 16, -13, 30, 22, 5,
             _shade(0, -13, 0, 9, (0.0, "#D4DBE0"), (0.5, "#8C959C"), (1.0, "#4E565C")),
             "#31373D")
    p.setPen(QPen(QColor("#3B4248"), 1.6))
    for i in range(6):
        x = 19 + i * 4.6
        p.drawLine(QPointF(x, -11), QPointF(x, 7))
    _rounded(p, 44, -6, 12, 9, 2, QColor("#22262A"))


def _tank_tool(p: QPainter, segments, nozzle="#C9D2D8") -> None:
    """Shared silhouette for the flame- and colour-thrower."""
    p.translate(50, 52)
    p.rotate(-38)
    # nozzle pointing up-left
    _rounded(p, -7, -54, 14, 28, 6,
             _shade(-7, 0, 7, 0, (0.0, "#F2F6F8"), (0.5, QColor(nozzle)), (1.0, "#6E777D")),
             "#596268")
    _rounded(p, -10, -32, 20, 9, 4, QColor("#7C868D"), "#596268")
    # tank
    tank = QRectF(-17, -28, 34, 62)
    path = QPainterPath()
    path.addRoundedRect(tank, 16, 16)
    p.save()
    p.setClipPath(path)
    count = len(segments)
    step = tank.height() / count
    for i, color in enumerate(segments):
        band = QRectF(tank.x(), tank.y() + i * step, tank.width(), step + 1)
        p.setPen(Qt.NoPen)
        p.setBrush(_shade(band.x(), 0, band.right(), 0,
                          (0.0, QColor(color).darker(150)),
                          (0.35, QColor(color)),
                          (1.0, QColor(color).darker(175))))
        p.drawRect(band)
        if count > 1:
            p.setPen(QPen(QColor(0, 0, 0, 70), 1.4))
            p.drawLine(QPointF(band.x(), band.y()), QPointF(band.right(), band.y()))
    p.restore()
    p.setPen(QPen(QColor(0, 0, 0, 90), 1.4))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)
    _gloss(p, -12, -22, 10, 46, 5, 120)
    _rounded(p, -14, 30, 28, 9, 4, QColor("#8A5A2B"), "#5E3D1C")


def _flamethrower(p: QPainter) -> None:
    _tank_tool(p, ["#FFA53A", "#F2761A", "#C64A08"])


def _colorthrower(p: QPainter) -> None:
    _tank_tool(p, ["#E43A4B", "#33B04A", "#2B6FD6"])


def _phaser(p: QPainter) -> None:
    p.translate(50, 52)
    p.rotate(-38)
    # emitter rail with its row of charge cells
    _rounded(p, -14, -48, 28, 34, 9,
             _shade(-14, 0, 14, 0, (0.0, "#8E1230"), (0.4, "#D6203F"), (1.0, "#7A0C22")),
             "#4F0716")
    p.setPen(Qt.NoPen)
    for i in range(4):
        p.setBrush(_shade(-6, 0, 6, 0, (0.0, "#7CF06A"), (0.5, "#2CB92C"), (1.0, "#0E7A1C")))
        p.drawRoundedRect(QRectF(-7, -45 + i * 7.6, 14, 6), 2, 2)
    # body
    _rounded(p, -16, -18, 32, 46, 13,
             _shade(-16, 0, 16, 0, (0.0, "#A05FD8"), (0.4, "#6B2AA8"), (1.0, "#331054")),
             "#25093E")
    _gloss(p, -11, -13, 9, 32, 4.5, 110)
    _rounded(p, -10, 24, 20, 16, 5,
             _shade(0, 24, 0, 40, (0.0, "#3A1660"), (1.0, "#140626")), "#0E0418")


def _stamp(p: QPainter) -> None:
    orange = _shade(30, 0, 76, 0, (0.0, "#FFB44A"),
                    (0.45, "#F2921C"), (1.0, "#C96C0A"))
    p.setPen(Qt.NoPen)
    p.setBrush(orange)
    p.drawEllipse(QRectF(36, 14, 30, 30))          # knob
    p.drawRoundedRect(QRectF(43, 32, 16, 24), 7, 7)  # neck
    path = QPainterPath()
    path.moveTo(44, 50)
    path.cubicTo(36, 58, 28, 62, 28, 74)
    path.cubicTo(28, 86, 38, 92, 51, 92)
    path.cubicTo(64, 92, 74, 86, 74, 74)
    path.cubicTo(74, 62, 66, 58, 58, 50)
    path.closeSubpath()
    p.drawPath(path)
    p.setBrush(QColor(0, 0, 0, 45))
    p.drawEllipse(QRectF(31, 80, 40, 12))
    p.setBrush(QColor(255, 255, 255, 90))
    p.drawEllipse(QRectF(41, 18, 9, 12))


def _termites(p: QPainter) -> None:
    # dirt mound they came out of
    mound = QPainterPath()
    mound.moveTo(14, 88)
    mound.cubicTo(28, 60, 70, 58, 88, 88)
    mound.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(_shade(0, 58, 0, 90, (0.0, "#8B5E33"), (1.0, "#4A2E15")))
    p.drawPath(mound)
    p.setBrush(QColor(0, 0, 0, 70))
    p.drawEllipse(QRectF(44, 74, 16, 9))

    def bug(x, y, angle, body, scale=1.0):
        p.save()
        p.translate(x, y)
        p.rotate(angle)
        p.scale(scale, scale)
        p.setPen(QPen(QColor("#1B1008"), 1.5))
        for i in range(3):
            ox = -5 + i * 5
            p.drawLine(QPointF(ox, -3), QPointF(ox - 4, -9))
            p.drawLine(QPointF(ox, 3), QPointF(ox - 4, 9))
        p.drawLine(QPointF(11, -2), QPointF(17, -7))
        p.drawLine(QPointF(11, 2), QPointF(17, 7))
        p.setPen(Qt.NoPen)
        p.setBrush(_shade(0, -6, 0, 6, (0.0, QColor(body).lighter(135)), (1.0, QColor(body))))
        p.drawEllipse(QRectF(-11, -6, 18, 12))
        p.drawEllipse(QRectF(2, -5, 11, 10))
        p.setBrush(QColor("#2A1A0C"))
        p.drawEllipse(QRectF(9, -4.5, 8, 9))
        p.restore()

    bug(56, 44, -18, "#8E2B1C", 1.15)
    bug(30, 68, 12, "#3E2712", 0.85)


def _washing(p: QPainter) -> None:
    p.translate(50, 50)
    p.rotate(-26)
    cyan = _shade(0, -14, 0, 14, (0.0, "#8FF6F6"), (0.35, "#2BD6D6"), (1.0, "#0B8E96"))
    # grip
    p.save()
    p.translate(-18, 8)
    p.rotate(16)
    _rounded(p, -9, 0, 19, 30, 5,
             _shade(-9, 0, 10, 0, (0.0, "#4FE3E3"), (1.0, "#0A7B84")), "#075E66")
    p.restore()
    # barrel
    _rounded(p, -30, -15, 62, 26, 9, cyan, "#075E66")
    _gloss(p, -26, -11, 46, 9, 4.5, 130)
    # reservoir bump and nozzle
    _rounded(p, -14, -25, 26, 14, 6,
             _shade(0, -25, 0, -11, (0.0, "#B6FBFB"), (1.0, "#25C2C6")), "#0A7B84")
    _rounded(p, 30, -8, 12, 12, 3, QColor("#0A7B84"), "#064A52")
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 160))
    for cx, cy, r in ((46, -12, 4.5), (54, -3, 3.0), (49, 6, 2.2)):
        p.setBrush(QColor(255, 255, 255, 120))
        p.drawEllipse(QPointF(cx, cy), r, r)


PAINTERS = {
    "hammer": _hammer,
    "chainsaw": _chainsaw,
    "machinegun": _machinegun,
    "flamethrower": _flamethrower,
    "colorthrower": _colorthrower,
    "phaser": _phaser,
    "stamp": _stamp,
    "termites": _termites,
    "washing": _washing,
}

_CACHE: dict[tuple[str, int, bool], QPixmap] = {}


def render(name: str, size: int, shadow: bool = False) -> QPixmap:
    """Cached pixmap of one tool, ``size`` px square, transparent background."""
    key = (name, size, shadow)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    painter.scale(size / BOX, size / BOX)
    if shadow:
        painter.save()
        painter.translate(3, 4)
        painter.setOpacity(0.30)
        blob = QRadialGradient(50, 55, 46)
        blob.setColorAt(0.0, QColor(0, 0, 0, 190))
        blob.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(blob)
        painter.drawEllipse(QRectF(2, 6, 96, 96))
        painter.restore()
    painter.save()
    PAINTERS[name](painter)
    painter.restore()
    painter.end()

    _CACHE[key] = pixmap
    return pixmap
