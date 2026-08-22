"""Milestone 4 checks for bubble truncation, following, timeout and edges."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QEventLoop, QRect, QTimer
from PyQt6.QtWidgets import QApplication

from app.speech_bubble import SpeechBubble


def inside(inner: QRect, outer: QRect) -> bool:
    return (
        inner.left() >= outer.left()
        and inner.top() >= outer.top()
        and inner.right() <= outer.right()
        and inner.bottom() <= outer.bottom()
    )


def main() -> None:
    app = QApplication.instance() or QApplication([])
    bubble = SpeechBubble(base_duration=40, max_length=80)
    screen = QRect(0, 0, 800, 600)
    long_text = "这是一段中文气泡测试。" * 30
    bubble.show_message(long_text, QRect(300, 300, 120, 180))
    assert len(bubble.shown_text) == 82 and bubble.shown_text.endswith("……")
    print("chinese_wrap_and_truncation=True")

    for name, pet_rect in {
        "top_left": QRect(0, 0, 120, 180),
        "top_right": QRect(680, 0, 120, 180),
        "bottom_left": QRect(0, 420, 120, 180),
        "bottom_right": QRect(680, 420, 120, 180),
        "center": QRect(340, 220, 120, 180),
    }.items():
        bubble.reposition(pet_rect, screen)
        assert inside(bubble.frameGeometry(), screen), name
    print("screen_edges_clamped=True")

    first = bubble.pos()
    moved_pet = QRect(520, 300, 120, 180)
    bubble.follow_pet(moved_pet)
    bubble.reposition(moved_pet, screen)
    assert bubble.pos() != first
    print("follows_pet=True")

    loop = QEventLoop()
    QTimer.singleShot(1800, loop.quit)
    loop.exec()
    assert bubble.isHidden()
    print("auto_hide=True")
    app.quit()


if __name__ == "__main__":
    main()
