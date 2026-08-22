"""Milestone 2 regression: every action returns to the exact base position."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QEventLoop, QPoint, QTimer
from PyQt6.QtWidgets import QApplication

from app.action_controller import ActionController


def wait_for_action(controller: ActionController, action: str) -> None:
    loop = QEventLoop()
    controller.action_finished.connect(loop.quit)
    assert controller.play(action)
    QTimer.singleShot(1000, loop.quit)
    loop.exec()
    try:
        controller.action_finished.disconnect(loop.quit)
    except TypeError:
        pass
    assert not controller.is_animating()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    controller = ActionController(action_duration=20, idle_duration=50)
    base_position = QPoint(640, 360)
    rendered_positions: list[QPoint] = []
    controller.offset_changed.connect(
        lambda offset: rendered_positions.append(base_position + offset)
    )

    for action in ("bounce", "nod", "shake", "wave"):
        for _ in range(20):
            wait_for_action(controller, action)
            assert controller.current_offset() == QPoint()
            assert base_position == QPoint(640, 360)
        print(f"{action}_20x_no_drift=True")

    controller.start_idle_breathing()
    QTimer.singleShot(120, app.quit)
    app.exec()
    controller.pause_for_drag()
    assert controller.current_offset() == QPoint()
    print(f"offset_samples={len(rendered_positions)}")
    print("drag_pause_resets_offset=True")


if __name__ == "__main__":
    main()
