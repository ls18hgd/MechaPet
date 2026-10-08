"""Checks settings character discovery, selection, and reload wiring."""

import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from app.character_manager import CharacterManager
from app.settings_window import SettingsWindow


app = QApplication.instance() or QApplication(sys.argv)
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    for pack_id, name in (("one", "角色一"), ("two", "角色二")):
        pack = root / pack_id
        frames = pack / "sprites" / "idle"
        frames.mkdir(parents=True)
        image = QImage(32, 32, QImage.Format.Format_ARGB32)
        image.fill(0)
        assert image.save(str(frames / "000.png"))
        (pack / "manifest.json").write_text(
            json.dumps(
                {
                    "id": pack_id,
                    "name": name,
                    "version": 1,
                    "canvas": {
                        "width": 32,
                        "height": 32,
                        "anchor_x": 16,
                        "anchor_y": 31,
                    },
                    "animations": {
                        "idle": {"path": "sprites/idle", "fps": 8, "loop": True}
                    },
                    "fallback_animation": "idle",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    settings = QSettings(str(root / "test.ini"), QSettings.Format.IniFormat)
    manager = CharacterManager(root, settings)
    window = SettingsWindow()
    window.set_character_manager(manager)
    assert window.character_combo.count() == 2
    index = window.character_combo.findData("two")
    window.character_combo.setCurrentIndex(index)
    assert manager.current.id == "two"
    assert settings.value("character/current_id") == "two"
    window._reload_characters()
    assert manager.current.id == "two"

print("character_list=True")
print("character_switch=True")
print("selection_persistence=True")
print("character_reload=True")

