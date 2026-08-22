"""Chat bubble UI displayed next to the desktop pet."""

from PyQt6.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import (
    QCloseEvent,
    QColor,
    QFont,
    QKeyEvent,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.ai_client import AIClient, AIClientError
from app.ai_response import AIResponse


class ChatWorker(QObject):
    """Execute one synchronous API request away from the GUI thread."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, client: AIClient, message: str) -> None:
        super().__init__()
        self._client = client
        self._message = message

    @pyqtSlot()
    def run(self) -> None:
        try:
            self.succeeded.emit(self._client.send_message(self._message))
        except AIClientError as exc:
            self.failed.emit(str(exc))
        except Exception:
            self.failed.emit("发生了意外错误，但桌宠仍然安全运行。请稍后重试。")
        finally:
            self.finished.emit()


class ChatWindow(QWidget):
    """A lightweight chat window whose close action only hides the window."""

    message_submitted = pyqtSignal(str)
    request_started = pyqtSignal()
    response_received = pyqtSignal(object)
    request_failed = pyqtSignal(str)

    def __init__(self, ai_client: AIClient | None = None, fake_reply: bool = False) -> None:
        super().__init__()
        self._ai_client = ai_client
        self._fake_reply = fake_reply
        self._busy = False
        self._thread: QThread | None = None
        self._worker: ChatWorker | None = None
        self._display_messages: list[dict[str, str]] = [
            {"role": "assistant", "content": "你好呀，我会一直在桌面陪着你。"}
        ]

        self.setWindowTitle("和 MechaPet 聊天")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setMinimumSize(360, 420)

        title = QLabel("MechaPet")
        title.setObjectName("title")
        self.history = QTextBrowser()
        self.history.setObjectName("history")
        self.history.setOpenExternalLinks(False)
        self._render_messages()

        self.input = QLineEdit()
        self.input.setPlaceholderText("想和我说什么？")
        self.input.returnPressed.connect(self.send_current_message)
        self.send_button = QPushButton("发送")
        self.send_button.clicked.connect(self.send_current_message)

        input_row = QHBoxLayout()
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.send_button)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(self.history, 1)
        layout.addLayout(input_row)
        self.setStyleSheet(
            """
            QWidget { background: #fff9f6; color: #3f3437; font-size: 14px; }
            QLabel#title { color: #b45d70; font-size: 20px; font-weight: 700; }
            QTextBrowser#history { background: white; border: 1px solid #efdadd;
                border-radius: 12px; padding: 8px; }
            QLineEdit { background: white; border: 1px solid #dfc6cc;
                border-radius: 10px; padding: 9px; }
            QPushButton { background: #d98294; color: white; border: none;
                border-radius: 10px; padding: 9px 16px; font-weight: 600; }
            QPushButton:disabled { background: #d7c8cb; }
            """
        )

    def send_current_message(self) -> None:
        message = self.input.text().strip()
        if not message or self._busy:
            return
        self.input.clear()
        self._display_messages.append({"role": "user", "content": message})
        self.message_submitted.emit(message)
        self._set_busy(True)
        self._display_messages.append(
            {"role": "status", "content": "_正在思考……_"}
        )
        self._render_messages()

        if self._fake_reply:
            QTimer.singleShot(450, lambda: self.show_reply(f"我听见啦：{message}"))
        elif self._ai_client is not None:
            self._start_ai_request(message)
        else:
            self.show_error("AI 客户端尚未初始化。")

    def _start_ai_request(self, message: str) -> None:
        self._thread = QThread(self)
        self._worker = ChatWorker(self._ai_client, message)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.succeeded.connect(self._handle_ai_response)
        self._worker.failed.connect(self._handle_ai_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker_refs)
        self.request_started.emit()
        self._thread.start()

    def _clear_worker_refs(self) -> None:
        self._thread = None
        self._worker = None

    def show_reply(self, reply: str) -> None:
        self._remove_status_message()
        self._display_messages.append({"role": "assistant", "content": reply})
        self._render_messages()
        self._set_busy(False)

    def show_error(self, error: str) -> None:
        self.show_reply(f"⚠ {error}")

    def _handle_ai_response(self, response: AIResponse) -> None:
        self.response_received.emit(response)
        self.show_reply(response.text)

    def _handle_ai_error(self, error: str) -> None:
        self.request_failed.emit(error)
        self.show_error(error)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.input.setEnabled(not busy)
        self.send_button.setEnabled(not busy)
        if not busy:
            self.input.setFocus()

    def _remove_status_message(self) -> None:
        if self._display_messages and self._display_messages[-1]["role"] == "status":
            self._display_messages.pop()

    def _render_messages(self) -> None:
        """Rebuild the display document with Qt's safe Markdown parser."""
        document = self.history.document()
        document.clear()
        cursor = QTextCursor(document)
        markdown_features = (
            QTextDocument.MarkdownFeature.MarkdownDialectGitHub
            | QTextDocument.MarkdownFeature.MarkdownNoHTML
        )

        for index, message in enumerate(self._display_messages):
            role = message["role"]
            label = "你：" if role == "user" else "MechaPet："
            label_format = QTextCharFormat()
            label_format.setFontWeight(QFont.Weight.Bold)
            label_format.setForeground(
                QColor("#557a95") if role == "user" else QColor("#b45d70")
            )
            cursor.insertText(label, label_format)
            cursor.insertBlock()
            cursor.insertMarkdown(message["content"], markdown_features)

            if index < len(self._display_messages) - 1:
                block_format = QTextBlockFormat()
                block_format.setTopMargin(4)
                block_format.setBottomMargin(8)
                cursor.insertBlock(block_format)

        self.history.moveCursor(QTextCursor.MoveOperation.End)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        event.ignore()
        self.hide()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
            return
        super().keyPressEvent(event)
