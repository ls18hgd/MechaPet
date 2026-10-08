"""Settings and local character selection without exposing secrets."""

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QCloseEvent, QDesktopServices
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.character_manager import CharacterManager
from app.config import PROJECT_ROOT, config


class SettingsWindow(QWidget):
    """Show configuration status without ever exposing the API key."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MechaPet 设置")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFixedWidth(420)
        self._character_manager: CharacterManager | None = None

        title = QLabel("设置")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #b45d70;")
        self.api_status = QLabel()
        self.api_status.setWordWrap(True)
        self.model_label = QLabel(f"当前模型：{config.deepseek_model}")
        self.character_label = QLabel("当前角色：尚未加载")
        self.character_combo = QComboBox()
        self.character_combo.currentIndexChanged.connect(self._select_character)
        reload_button = QPushButton("重新加载角色")
        reload_button.clicked.connect(self._reload_characters)
        folder_button = QPushButton("打开角色目录")
        folder_button.clicked.connect(self._open_character_folder)
        character_buttons = QHBoxLayout()
        character_buttons.addWidget(reload_button)
        character_buttons.addWidget(folder_button)
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
        layout.addWidget(self.character_label)
        layout.addWidget(self.character_combo)
        layout.addLayout(character_buttons)
        layout.addWidget(env_label)
        layout.addWidget(close_button)
        self.setStyleSheet(
            "QWidget { background: #fff9f6; color: #3f3437; font-size: 14px; }"
            "QPushButton { background: #d98294; color: white; border: none; "
            "border-radius: 8px; padding: 8px 14px; }"
        )
        self.refresh()

    def set_character_manager(self, manager: CharacterManager) -> None:
        self._character_manager = manager
        manager.characters_reloaded.connect(self._populate_characters)
        manager.character_changed.connect(lambda _pack: self._populate_characters())
        self._populate_characters()

    def refresh(self) -> None:
        state = "已配置" if config.deepseek_api_key else "未配置"
        hint = "" if config.deepseek_api_key else "（请按 README 创建 .env）"
        self.api_status.setText(f"DeepSeek API Key：{state}{hint}")
        self._populate_characters()

    def _populate_characters(self) -> None:
        manager = self._character_manager
        if manager is None:
            return
        current_id = manager.current.id
        self.character_combo.blockSignals(True)
        self.character_combo.clear()
        for pack in manager.available():
            self.character_combo.addItem(pack.name, pack.id)
        index = self.character_combo.findData(current_id)
        self.character_combo.setCurrentIndex(max(0, index))
        self.character_combo.blockSignals(False)
        self.character_label.setText(f"当前角色：{manager.current.name}")

    def _select_character(self, index: int) -> None:
        if self._character_manager is None or index < 0:
            return
        character_id = self.character_combo.itemData(index)
        if character_id and character_id != self._character_manager.current.id:
            self._character_manager.select(character_id)

    def _reload_characters(self) -> None:
        if self._character_manager is not None:
            self._character_manager.reload()

    def _open_character_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(PROJECT_ROOT / "characters")))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        event.ignore()
        self.hide()
