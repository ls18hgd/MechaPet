"""Short-lived, screen-aware speech bubble shown beside the pet."""

from PyQt6.QtCore import QRect, QSize, Qt, QTimer
from PyQt6.QtGui import QFontMetrics, QGuiApplication, QTextDocument
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.config import SPEECH_BUBBLE_BASE_DURATION, SPEECH_BUBBLE_MAX_LENGTH


class SpeechBubble(QWidget):
    """A non-activating tool window for short reply previews."""

    MAX_CONTENT_WIDTH = 280
    GAP = 12

    def __init__(
        self,
        base_duration: int = SPEECH_BUBBLE_BASE_DURATION,
        max_length: int = SPEECH_BUBBLE_MAX_LENGTH,
    ) -> None:
        super().__init__()
        self.base_duration = base_duration
        self.max_length = max_length
        self._last_pet_geometry = QRect()
        self._shown_text = ""

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.label.setMaximumWidth(self.MAX_CONTENT_WIDTH)
        self.label.setStyleSheet(
            "QLabel { background: #fff9f6; color: #3f3437; "
            "border: 1px solid #e8cfd5; border-radius: 14px; "
            "padding: 11px 14px; font-size: 14px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    @property
    def shown_text(self) -> str:
        return self._shown_text

    def show_message(self, text: str, pet_geometry: QRect) -> None:
        self._shown_text = self._truncate(self._plain_preview(text.strip()))
        self.label.setText(self._shown_text)
        self._resize_for_text()
        self._last_pet_geometry = QRect(pet_geometry)
        self.reposition(pet_geometry)
        self.show()
        self.raise_()
        duration = min(8000, self.base_duration + len(self._shown_text) * 20)
        self._hide_timer.start(duration)

    def follow_pet(self, pet_geometry: QRect) -> None:
        self._last_pet_geometry = QRect(pet_geometry)
        if self.isVisible():
            self.reposition(pet_geometry)

    def reposition(
        self, pet_geometry: QRect, available_geometry: QRect | None = None
    ) -> None:
        available = available_geometry or self._available_geometry(pet_geometry)
        width, height = self.width(), self.height()
        gap = self.GAP

        top = (
            pet_geometry.center().x() - width // 2,
            pet_geometry.top() - height - gap,
        )
        left = (
            pet_geometry.left() - width - gap,
            pet_geometry.center().y() - height // 2,
        )
        right = (
            pet_geometry.right() + gap,
            pet_geometry.center().y() - height // 2,
        )
        bottom = (
            pet_geometry.center().x() - width // 2,
            pet_geometry.bottom() + gap,
        )

        if top[1] >= available.top():
            x, y = top
        elif left[0] >= available.left():
            x, y = left
        elif right[0] + width <= available.right() + 1:
            x, y = right
        else:
            x, y = bottom

        max_x = max(available.left(), available.right() - width + 1)
        max_y = max(available.top(), available.bottom() - height + 1)
        self.move(
            min(max(x, available.left()), max_x),
            min(max(y, available.top()), max_y),
        )

    def _available_geometry(self, pet_geometry: QRect) -> QRect:
        screen = QGuiApplication.screenAt(pet_geometry.center())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry() if screen is not None else QRect(0, 0, 1920, 1080)

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_length:
            return text
        return text[: self.max_length].rstrip() + "……"

    @staticmethod
    def _plain_preview(text: str) -> str:
        document = QTextDocument()
        document.setMarkdown(
            text,
            QTextDocument.MarkdownFeature.MarkdownDialectGitHub
            | QTextDocument.MarkdownFeature.MarkdownNoHTML,
        )
        return document.toPlainText().strip()

    def _resize_for_text(self) -> None:
        metrics = QFontMetrics(self.label.font())
        bounds = metrics.boundingRect(
            QRect(0, 0, self.MAX_CONTENT_WIDTH - 28, 1000),
            Qt.TextFlag.TextWordWrap,
            self._shown_text,
        )
        content = QSize(
            min(self.MAX_CONTENT_WIDTH, max(100, bounds.width() + 30)),
            max(48, bounds.height() + 24),
        )
        self.label.setFixedSize(content)
        self.setFixedSize(content)
