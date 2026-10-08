"""Milestone 1 checks for character discovery, fallback, and path safety."""

import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QColor, QImage

from app.character_manager import CharacterManager
from app.character_pack import CharacterPack, CharacterPackError


def write_png(path: Path, width: int = 8, height: int = 10) -> None:
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor(255, 100, 120, 180))
    assert image.save(str(path), "PNG")


def make_pack(root: Path, pack_id: str = "sample") -> Path:
    pack = root / pack_id
    frames = pack / "sprites" / "idle"
    frames.mkdir(parents=True)
    write_png(frames / "000.png")
    (pack / "manifest.json").write_text(
        json.dumps(
            {
                "id": pack_id,
                "name": "测试角色",
                "version": 1,
                "canvas": {"width": 8, "height": 10, "anchor_x": 4, "anchor_y": 10},
                "animations": {
                    "idle": {"path": "sprites/idle", "fps": 8, "loop": True}
                },
                "fallback_animation": "idle",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return pack


def main() -> None:
    project_pack = CharacterPack.load(Path("characters/default"))
    assert project_pack.get_animation("walk").name == "idle"
    assert project_pack.get_animation("idle").frames[0].name == "000.png"
    print("default_pack_and_fallback=True")

    with TemporaryDirectory() as temp:
        root = Path(temp)
        make_pack(root)
        settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
        manager = CharacterManager(root, settings)
        assert manager.current_id == "sample"
        assert manager.available()[0].name == "测试角色"
        manager.reload()
        print("discovery_reload_persistence=True")

        unsafe = make_pack(root, "unsafe")
        payload = json.loads((unsafe / "manifest.json").read_text(encoding="utf-8"))
        payload["animations"]["idle"]["path"] = "../../outside"
        (unsafe / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
        try:
            CharacterPack.load(unsafe)
        except CharacterPackError:
            print("path_traversal_rejected=True")
        else:
            raise AssertionError("path traversal was accepted")

        wrong = make_pack(root, "wrong-size")
        write_png(wrong / "sprites" / "idle" / "001.png", 9, 10)
        try:
            CharacterPack.load(wrong)
        except CharacterPackError:
            print("frame_size_validation=True")
        else:
            raise AssertionError("wrong frame size was accepted")


if __name__ == "__main__":
    main()
