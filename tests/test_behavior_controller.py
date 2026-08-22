"""Milestone 7 checks for idle scheduling and safety gates."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication

from app.behavior_controller import BehaviorController
from app.pet_state import PetState
from app.pet_window import PetWindow


def wait(milliseconds: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    allowed = False
    performed: list[bool] = []
    behavior = BehaviorController(
        can_run=lambda: allowed,
        perform=lambda: performed.append(True),
        min_seconds=0.03,
        max_seconds=0.03,
    )
    behavior.start()
    wait(80)
    assert not performed
    allowed = True
    behavior.reset_after_interaction()
    wait(50)
    assert len(performed) == 1
    behavior.stop()
    print("timer_gate_and_reset=True")

    pet = PetWindow()
    controller = pet._controller
    # Subtle idle breathing is allowed to yield to an autonomous action.
    assert controller._can_run_idle_behavior()
    controller.state.set_state(PetState.THINKING)
    assert not controller._can_run_idle_behavior()
    controller.state.restore_idle()
    controller.actions.pause_for_drag()
    assert not controller._can_run_idle_behavior()
    controller.actions.resume_after_drag(resume_idle=False)
    controller.actions.play("bounce")
    assert not controller._can_run_idle_behavior()
    print("thinking_dragging_action_blocked=True")
    controller.prepare_to_quit()
    app.quit()


if __name__ == "__main__":
    main()
