"""Milestone 2 tests for loop, one-shot, fallback, direction, and GUI thread."""

import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QEventLoop, QThread, QTimer
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication

from app.character_pack import CharacterPack
from app.sprite_animator import SpriteAnimator


def save_frame(path: Path, color: QColor) -> None:
    image = QImage(12, 16, QImage.Format.Format_ARGB32)
    image.fill(color)
    assert image.save(str(path), "PNG")


def make_pack(root: Path) -> CharacterPack:
    pack = root / "animated"
    for name in ("idle", "wave"):
        (pack / "sprites" / name).mkdir(parents=True)
    save_frame(pack / "sprites" / "idle" / "000.png", QColor("red"))
    save_frame(pack / "sprites" / "idle" / "001.png", QColor("green"))
    save_frame(pack / "sprites" / "wave" / "000.png", QColor("blue"))
    save_frame(pack / "sprites" / "wave" / "001.png", QColor("yellow"))
    (pack / "manifest.json").write_text(
        json.dumps(
            {
                "id": "animated",
                "name": "Animated",
                "version": 1,
                "canvas": {"width": 12, "height": 16, "anchor_x": 6, "anchor_y": 16},
                "animations": {
                    "idle": {"path": "sprites/idle", "fps": 30, "loop": True},
                    "wave": {"path": "sprites/wave", "fps": 30, "loop": False},
                },
                "fallback_animation": "idle",
            }
        ),
        encoding="utf-8",
    )
    return CharacterPack.load(pack)


def wait(milliseconds: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as temp:
        animator = SpriteAnimator(target_height=160)
        animator.set_character(make_pack(Path(temp)))
        frames = []
        gui_threads = []
        finished = []
        animator.frame_changed.connect(
            lambda frame: (
                frames.append(frame.cacheKey()),
                gui_threads.append(QThread.currentThread() is app.thread()),
            )
        )
        animator.animation_finished.connect(finished.append)

        assert animator.play("idle")
        wait(110)
        assert len(frames) >= 3 and len(set(frames)) >= 2
        assert all(gui_threads)
        print("loop_and_gui_thread=True")

        before_flip = frames[-1]
        animator.set_direction("left")
        assert frames[-1] != before_flip
        print("direction_flip=True")

        assert animator.play("wave")
        wait(100)
        assert finished == ["wave"] and not animator.is_playing()
        print("one_shot_finished=True")

        assert animator.play("missing")
        assert animator.current_animation == "missing"
        wait(40)
        assert animator.is_playing()
        print("missing_animation_fallback=True")
        animator.stop()
    app.quit()


if __name__ == "__main__":
    main()
