"""Minimal settings/status window for V0.1."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from app.config import PROJECT_ROOT, config


class SettingsWindow(QWidget):
    """Show configuration status without ever exposing the API key."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MechaPet 设置")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFixedWidth(420)

        title = QLabel("设置")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #b45d70;")
        self.api_status = QLabel()
        self.api_status.setWordWrap(True)
        self.model_label = QLabel(f"当前模型：{config.deepseek_model}")
        env_label = QLabel(f"配置文件：{PROJECT_ROOT / '.env'}")
        env_label.setWordWrap(True)
        close_button = QPushButton("完成")
        close_button.clicked.connect(self.hide)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(self.api_status)
        layout.addWidget(self.model_label)
        layout.addWidget(env_label)
        layout.addWidget(close_button)
        self.setStyleSheet(
            "QWidget { background: #fff9f6; color: #3f3437; font-size: 14px; }"
            "QPushButton { background: #d98294; color: white; border: none; "
            "border-radius: 8px; padding: 8px 14px; }"
        )
        self.refresh()

    def refresh(self) -> None:
        state = "已配置" if config.deepseek_api_key else "未配置"
        hint = "" if config.deepseek_api_key else "（请按 README 创建 .env）"
        self.api_status.setText(f"DeepSeek API Key：{state}{hint}")

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        event.ignore()
        self.hide()
