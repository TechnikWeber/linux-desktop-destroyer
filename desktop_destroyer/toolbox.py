"""The weapon panel.

Drawn inside the fullscreen window rather than as a separate top-level, which
keeps it identical on X11 and Wayland (where clients may not position their
own windows).  Drag it by its title bar.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient

from . import icons

BACKGROUND = QColor("#291963")
BORDER = QColor("#5B3FC4")
SELECT = QColor("#6C4BE0")
TITLE_BG = QColor("#1B0F46")

COLUMNS = 3
CELL_W = 168.0
CELL_H = 116.0
PAD = 12.0
TITLE_H = 34.0
FOOTER_H = 46.0
ICON = 64


class Toolbox:
    def __init__(self, weapons, x: float = 60.0, y: float = 60.0) -> None:
        self.weapons = weapons
        self.pos = QPointF(x, y)
        self.visible = True
        self._drag_offset: QPointF | None = None
        rows = (len(weapons) + COLUMNS - 1) // COLUMNS
        self.size = (COLUMNS * CELL_W + 2 * PAD,
                     TITLE_H + rows * CELL_H + FOOTER_H + PAD)

    # -- geometry ----------------------------------------------------------

    def rect(self) -> QRectF:
        return QRectF(self.pos.x(), self.pos.y(), self.size[0], self.size[1])

    def cell_rect(self, index: int) -> QRectF:
        column, row = index % COLUMNS, index // COLUMNS
        return QRectF(self.pos.x() + PAD + column * CELL_W,
                      self.pos.y() + TITLE_H + row * CELL_H,
                      CELL_W, CELL_H)

    def title_rect(self) -> QRectF:
        return QRectF(self.pos.x(), self.pos.y(), self.size[0], TITLE_H)

    def close_rect(self) -> QRectF:
        return QRectF(self.pos.x() + self.size[0] - 30, self.pos.y() + 7, 22, 20)

    def clamp_into(self, width: float, height: float) -> None:
        x = min(max(self.pos.x(), -self.size[0] + 120), width - 120)
        y = min(max(self.pos.y(), 0.0), height - TITLE_H)
        self.pos = QPointF(x, y)

    # -- interaction -------------------------------------------------------

    def press(self, point: QPointF) -> str | int | None:
        """Returns 'close', 'drag', a weapon index, 'panel', or None if outside."""
        if not self.visible or not self.rect().contains(point):
            return None
        if self.close_rect().contains(point):
            return "close"
        if self.title_rect().contains(point):
            self._drag_offset = point - self.pos
            return "drag"
        for index in range(len(self.weapons)):
            if self.cell_rect(index).contains(point):
                return index
        return "panel"

    def drag(self, point: QPointF, bounds) -> bool:
        if self._drag_offset is None:
            return False
        self.pos = point - self._drag_offset
        self.clamp_into(bounds.width(), bounds.height())
        return True

    def release(self) -> None:
        self._drag_offset = None

    @property
    def dragging(self) -> bool:
        return self._drag_offset is not None

    # -- painting ----------------------------------------------------------

    def draw(self, p: QPainter, active: int) -> None:
        if not self.visible:
            return
        box = self.rect()

        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 110))
        p.drawRoundedRect(box.translated(5, 7), 12, 12)

        p.setBrush(BACKGROUND)
        p.setPen(QPen(BORDER, 2))
        p.drawRoundedRect(box, 12, 12)

        # title bar
        p.setPen(Qt.NoPen)
        p.setBrush(TITLE_BG)
        p.drawRoundedRect(QRectF(box.x() + 2, box.y() + 2, box.width() - 4, TITLE_H), 10, 10)
        p.drawRect(QRectF(box.x() + 2, box.y() + TITLE_H - 6, box.width() - 4, 6))

        font = QFont("DejaVu Sans", 11)
        font.setBold(True)
        font.setLetterSpacing(QFont.PercentageSpacing, 135)
        p.setFont(font)
        p.setPen(QColor("#C9B8FF"))
        p.drawText(QRectF(box.x() + 14, box.y(), box.width() - 40, TITLE_H),
                   Qt.AlignVCenter | Qt.AlignLeft, "DESKTOP DESTROYER")

        close = self.close_rect()
        p.setPen(QPen(QColor("#C9B8FF"), 2))
        p.drawLine(close.topLeft() + QPointF(6, 5), close.bottomRight() - QPointF(6, 5))
        p.drawLine(close.topRight() + QPointF(-6, 5), close.bottomLeft() - QPointF(-6, 5))

        # cells
        label_font = QFont("DejaVu Sans", 11)
        label_font.setBold(True)
        for index, weapon in enumerate(self.weapons):
            cell = self.cell_rect(index)
            if index == active:
                glow = QRadialGradient(cell.center(), cell.width() * 0.6)
                glow.setColorAt(0.0, QColor(SELECT.red(), SELECT.green(), SELECT.blue(), 190))
                glow.setColorAt(1.0, QColor(SELECT.red(), SELECT.green(), SELECT.blue(), 30))
                p.setPen(QPen(QColor("#B9A2FF"), 2))
                p.setBrush(glow)
                p.drawRoundedRect(cell.adjusted(6, 4, -6, -4), 9, 9)

            p.drawPixmap(QPointF(cell.center().x() - ICON / 2, cell.y() + 8),
                         icons.render(weapon.key, ICON))
            p.setFont(label_font)
            p.setPen(QColor(0, 0, 0, 150))
            text = f"{weapon.number}: {weapon.label}"
            p.drawText(cell.adjusted(1, 1, 1, 1).adjusted(0, ICON + 14, 0, 0),
                       Qt.AlignHCenter | Qt.AlignTop, text)
            p.setPen(QColor("#FFFFFF") if index == active else QColor("#E6DEFF"))
            p.drawText(cell.adjusted(0, ICON + 14, 0, 0),
                       Qt.AlignHCenter | Qt.AlignTop, text)

        # footer
        hint_font = QFont("DejaVu Sans", 9)
        p.setFont(hint_font)
        p.setPen(QColor("#9B87DE"))
        footer = QRectF(box.x() + PAD, box.bottom() - FOOTER_H,
                        box.width() - 2 * PAD, FOOTER_H - 6)
        p.drawText(footer, Qt.AlignHCenter | Qt.AlignTop,
                   "1–9 Werkzeug   ·   Tab Werkzeugkasten   ·   R Reparieren\n"
                   "S Speichern   ·   M Ton   ·   Esc Beenden")
        p.restore()
