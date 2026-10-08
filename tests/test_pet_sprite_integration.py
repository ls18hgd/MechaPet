"""Milestone 3 check that PetWindow is rendered by SpriteAnimator."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication

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
    assert controller.characters.current_id == "default"
    assert controller.sprite_animator.current_animation == "idle"
    assert not pet._pixmap.isNull() and pet._pixmap.height() == pet.PET_HEIGHT
    print("window_uses_default_character_pack=True")

    controller.state.set_state(PetState.HAPPY)
    wait(30)
    assert controller.sprite_animator.current_animation == "happy"
    assert controller.characters.current.get_animation("happy").name == "idle"
    print("state_to_sprite_fallback=True")

    controller.state.restore_idle()
    wait(30)
    assert controller.sprite_animator.current_animation == "idle"
    assert pet.isVisible()
    print("sprite_to_window_frame=True")
    controller.prepare_to_quit()
    app.quit()


if __name__ == "__main__":
    main()
