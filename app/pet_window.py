"""Transparent, draggable desktop pet window."""

from PyQt6.QtCore import QPoint, QRect, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QMouseEvent, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

from app.chat_window import ChatWindow
from app.ai_client import AIClient
from app.conversation_store import ConversationStore
from app.pet_controller import PetController
from app.settings_window import SettingsWindow


class PetWindow(QWidget):
    """A frameless always-on-top window that displays the pet sprite."""

    pet_geometry_changed = pyqtSignal(QRect)

    PET_HEIGHT = 320

    def __init__(self) -> None:
        super().__init__()
        self._drag_offset: QPoint | None = None
        self._press_global: QPoint | None = None
        self._dragged = False
        self._suppress_release_click = False
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(QApplication.doubleClickInterval())
        self._click_timer.timeout.connect(self._controller_click)
        self._base_position = QPoint()
        self._movement_position = QPoint()
        self._animation_offset = QPoint()
        self._pixmap = QPixmap()
        self._ai_client = AIClient()
        self._chat_window = ChatWindow(
            ai_client=self._ai_client,
            history_store=ConversationStore(),
        )
        self._settings_window = SettingsWindow()
        self._controller = PetController(
            apply_pixmap=self.set_pet_pixmap,
            apply_offset=self.apply_animation_offset,
            show_chat=self.show_chat,
            pet_geometry=self.frameGeometry,
            get_movement_position=self.movement_position,
            apply_movement_position=self.apply_movement_position,
            commit_movement_position=self.commit_movement_position,
            get_pet_size=self.size,
            get_available_geometry=self.current_available_geometry,
        )
        self._settings_window.set_character_manager(self._controller.characters)
        self.pet_geometry_changed.connect(self._controller.handle_pet_moved)
        self._chat_window.message_submitted.connect(
            lambda _message: self._controller.mark_interaction()
        )
        self._chat_window.request_started.connect(self._controller.handle_ai_started)
        self._chat_window.response_received.connect(
            self._controller.handle_ai_response
        )
        self._chat_window.request_failed.connect(self._controller.handle_ai_error)

        self.setWindowTitle("MechaPet")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self._controller.start()
        self._move_to_bottom_right()

    def set_pet_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap if not pixmap.isNull() else self._placeholder_pixmap()
        self.setFixedSize(self._pixmap.size())
        self.update()

    def set_base_position(self, position: QPoint) -> None:
        self._base_position = QPoint(position)
        self._movement_position = QPoint(position)
        self._apply_window_position()
        self.pet_geometry_changed.emit(self.frameGeometry())

    def base_position(self) -> QPoint:
        return QPoint(self._base_position)

    def movement_position(self) -> QPoint:
        return QPoint(self._movement_position)

    def apply_movement_position(self, position: QPoint) -> None:
        self._movement_position = QPoint(position)
        self._apply_window_position()
        self.pet_geometry_changed.emit(self.frameGeometry())

    def commit_movement_position(self, position: QPoint) -> None:
        self._base_position = QPoint(position)
        self._movement_position = QPoint(position)
        self._apply_window_position()
        self.pet_geometry_changed.emit(self.frameGeometry())

    def apply_animation_offset(self, offset: QPoint) -> None:
        self._animation_offset = QPoint(offset)
        self._apply_window_position()
        self.pet_geometry_changed.emit(self.frameGeometry())

    def _apply_window_position(self) -> None:
        QWidget.move(self, self._movement_position + self._animation_offset)

    def current_available_geometry(self) -> QRect:
        screen = self.screen() or QApplication.primaryScreen()
        return screen.availableGeometry() if screen is not None else QRect(0, 0, 1920, 1080)

    def _placeholder_pixmap(self) -> QPixmap:
        """Create a friendly fallback so a missing asset never crashes startup."""
        pixmap = QPixmap(240, 280)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#f7d6d9"))
        painter.setPen(QColor("#45383b"))
        painter.drawEllipse(35, 25, 170, 170)
        painter.setBrush(QColor("#2f292a"))
        painter.drawEllipse(80, 90, 15, 20)
        painter.drawEllipse(145, 90, 15, 20)
        painter.drawArc(95, 115, 50, 35, 200 * 16, 140 * 16)
        painter.setPen(QColor("#6b4f53"))
        painter.drawText(
            pixmap.rect().adjusted(12, 205, -12, -10),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            "MechaPet\n缺少 assets/pet.png",
        )
        painter.end()
        return pixmap

    def _move_to_bottom_right(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        margin = 24
        self.set_base_position(QPoint(
            area.right() - self.width() - margin,
            area.bottom() - self.height() - margin,
        ))

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(0, 0, self._pixmap)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._controller.handle_drag_started()
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            self._press_global = event.globalPosition().toPoint()
            self._dragged = False
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._controller.mark_interaction()
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if (
            self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            current_global = event.globalPosition().toPoint()
            if self._press_global is not None:
                distance = (current_global - self._press_global).manhattanLength()
                self._dragged = self._dragged or distance >= QApplication.startDragDistance()
            self.set_base_position(current_global - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            self._press_global = None
            self._controller.handle_drag_finished()
            if self._suppress_release_click:
                self._suppress_release_click = False
            elif not self._dragged:
                self._click_timer.start()
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._click_timer.stop()
            self._suppress_release_click = True
            self._controller.handle_double_click()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _controller_click(self) -> None:
        self._controller.handle_click()

    def _show_context_menu(self, position: QPoint) -> None:
        menu = QMenu(self)
        chat_action = QAction("聊天", menu)
        chat_action.triggered.connect(self.show_chat)
        settings_action = QAction("设置", menu)
        settings_action.triggered.connect(self.show_settings)
        exit_action = QAction("退出", menu)
        exit_action.triggered.connect(self.quit_application)
        menu.addAction(chat_action)
        menu.addAction(settings_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        menu.exec(position)

    def quit_application(self) -> None:
        self._controller.prepare_to_quit()
        QApplication.instance().quit()

    def show_chat(self) -> None:
        """Show and focus the persistent chat window next to the pet."""
        chat = self._chat_window
        screen = self.screen() or QApplication.primaryScreen()
        target_x = self.x() - chat.width() - 12
        target_y = self.y() + max(0, self.height() - chat.height())
        if screen is not None:
            area = screen.availableGeometry()
            if target_x < area.left():
                target_x = self.x() + self.width() + 12
            target_x = min(max(target_x, area.left()), area.right() - chat.width())
            target_y = min(max(target_y, area.top()), area.bottom() - chat.height())
        chat.move(target_x, target_y)
        chat.show()
        chat.raise_()
        chat.activateWindow()
        chat.input.setFocus()

    def show_settings(self) -> None:
        self._settings_window.refresh()
        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()

    def closeEvent(self, event) -> None:  # noqa: N802
        """Keep the pet alive unless the explicit Exit action is used."""
        event.ignore()
        self.hide()
