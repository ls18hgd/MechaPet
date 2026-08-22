"""Milestone 3 checks for idle, click, double-click, and drag coordination."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QEventLoop, QPoint, QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from app.pet_state import PetState
from app.pet_window import PetWindow


def wait(milliseconds: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    pet = PetWindow()
    pet.show()
    controller = pet._controller

    wait(1700)
    assert abs(controller.actions.current_offset().y()) <= 2
    controller.actions.pause_for_drag()
    assert controller.actions.current_offset() == QPoint()
    print("idle_breathing_subtle=True")

    controller.actions.resume_after_drag()
    controller.handle_click()
    assert controller.state.get_state() in {PetState.HAPPY, PetState.CURIOUS}
    assert controller.actions.is_animating()
    wait(1000)
    assert controller.state.get_state() is PetState.IDLE
    print("click_feedback_then_idle=True")

    original_chat = pet._chat_window
    QTest.mouseDClick(
        pet,
        Qt.MouseButton.LeftButton,
        pos=QPoint(pet.width() // 2, pet.height() // 2),
    )
    wait(50)
    assert pet._chat_window is original_chat and original_chat.isVisible()
    original_chat.close()
    assert pet.isVisible()
    print("double_click_reuses_chat=True")

    controller.actions.play("shake")
    old_base = pet.base_position()
    QTest.mousePress(pet, Qt.MouseButton.LeftButton, pos=QPoint(40, 40))
    QTest.mouseMove(pet, QPoint(100, 85), delay=20)
    QTest.mouseRelease(pet, Qt.MouseButton.LeftButton, pos=QPoint(100, 85))
    new_base = pet.base_position()
    assert new_base != old_base
    assert controller.actions.current_offset() == QPoint()
    assert pet.pos() == new_base
    print("drag_updates_base_without_conflict=True")
    app.quit()


if __name__ == "__main__":
    main()
