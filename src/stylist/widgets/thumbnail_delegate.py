"""ThumbnailDelegate — custom QStyledItemDelegate for the style gallery.

Each gallery item is rendered as a square thumbnail card with the style
name centred below the image.

An item can be flagged as *invalid* by setting ``Qt.UserRole + 1`` to
``True`` on the ``QStandardItem``.  Invalid items receive a translucent
grey overlay with a ⚠ warning badge.
"""
from __future__ import annotations

from PySide6.QtCore import QModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

THUMB_SIZE: int = 110
ITEM_WIDTH: int = 130
ITEM_HEIGHT: int = 148
PADDING: int = 6
FONT_SIZE: int = 9

# UserRole used to flag an item as invalid (broken chain / missing style)
INVALID_ROLE: int = Qt.UserRole + 1  # type: ignore[attr-defined]
# UserRole used to flag a system (built-in) chain item — renders a lock overlay
BUILTIN_ROLE: int = Qt.UserRole + 2  # type: ignore[attr-defined]
# UserRole used to flag the sentinel "+" add item
ADD_ITEM_ROLE: int = Qt.UserRole + 3  # type: ignore[attr-defined]


class ThumbnailDelegate(QStyledItemDelegate):
    """Renders each gallery item as a fixed-size thumbnail card with a name label."""

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        painter.save()
        rect = option.rect

        # ----------------------------------------------------------------
        # "+" add-item sentinel — completely custom rendering
        # ----------------------------------------------------------------
        if index.data(ADD_ITEM_ROLE):
            if option.state & QStyle.State_Selected:  # type: ignore[attr-defined]
                painter.fillRect(rect, option.palette.highlight())
            else:
                painter.fillRect(rect, QColor("#4a4a4a"))
            plus_font = QFont()
            plus_font.setPointSize(32)
            plus_font.setBold(True)
            painter.setFont(plus_font)
            painter.setPen(QColor("#aaaaaa"))
            painter.drawText(rect, Qt.AlignCenter, "+")  # type: ignore[attr-defined]
            painter.restore()
            return

        # Background
        if option.state & QStyle.State_Selected:  # type: ignore[attr-defined]
            painter.fillRect(rect, option.palette.highlight())
        else:
            painter.fillRect(rect, QColor("#3c3f41"))

        # Thumbnail — DecorationRole can return QPixmap or QIcon depending on how
        # the item was constructed; normalise to QPixmap.
        raw = index.data(Qt.DecorationRole)  # type: ignore[attr-defined]
        if isinstance(raw, QIcon):
            pixmap: QPixmap | None = raw.pixmap(THUMB_SIZE, THUMB_SIZE)
        else:
            pixmap = raw  # already QPixmap or None
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(
                THUMB_SIZE, THUMB_SIZE,
                Qt.KeepAspectRatio,  # type: ignore[attr-defined]
                Qt.SmoothTransformation,  # type: ignore[attr-defined]
            )
            px = rect.x() + (ITEM_WIDTH - scaled.width()) // 2
            py = rect.y() + PADDING
            painter.drawPixmap(px, py, scaled)

        # Name label
        name: str | None = index.data(Qt.DisplayRole)  # type: ignore[attr-defined]
        if name:
            if option.state & QStyle.State_Selected:  # type: ignore[attr-defined]
                painter.setPen(option.palette.highlightedText().color())
            else:
                painter.setPen(QColor("#dddddd"))
            font = QFont()
            font.setPointSize(FONT_SIZE)
            painter.setFont(font)
            text_top = rect.y() + THUMB_SIZE + PADDING * 2
            text_rect = QRect(rect.x(), text_top, ITEM_WIDTH, ITEM_HEIGHT - THUMB_SIZE - PADDING * 2)
            painter.drawText(
                text_rect,
                Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,  # type: ignore[attr-defined]
                name,
            )

        # Invalid overlay — translucent grey wash + ⚠ badge
        if index.data(INVALID_ROLE):
            overlay_rect = QRect(rect.x(), rect.y(), ITEM_WIDTH, THUMB_SIZE + PADDING)
            painter.fillRect(overlay_rect, QColor(0, 0, 0, 130))
            painter.setPen(QColor("#FFC107"))
            badge_font = QFont()
            badge_font.setPointSize(20)
            badge_font.setBold(True)
            painter.setFont(badge_font)
            painter.drawText(
                overlay_rect,
                Qt.AlignCenter,  # type: ignore[attr-defined]
                "\u26a0",
            )

        # Lock overlay (bottom-right) — indicates system/built-in chain
        if index.data(BUILTIN_ROLE):
            lock_size = 16
            lock_x = rect.x() + ITEM_WIDTH - lock_size - 4
            lock_y = rect.y() + THUMB_SIZE + PADDING - lock_size - 2
            lock_rect = QRect(lock_x, lock_y, lock_size, lock_size)
            lock_font = QFont()
            lock_font.setPointSize(10)
            painter.setFont(lock_font)
            painter.setOpacity(0.6)
            painter.setPen(QColor("#dddddd"))
            painter.drawText(lock_rect, Qt.AlignCenter, "\U0001f512")  # type: ignore[attr-defined]
            painter.setOpacity(1.0)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(ITEM_WIDTH, ITEM_HEIGHT)
