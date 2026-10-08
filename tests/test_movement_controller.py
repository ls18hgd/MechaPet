"""Executable checks for bounded, drift-free property animation movement."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import QEventLoop, QPoint, QRect, QSize, QTimer
from PyQt6.QtWidgets import QApplication

from app.movement_controller import MovementController


app = QApplication.instance() or QApplication(sys.argv)
position = QPoint(100, 200)
area = QRect(0, 0, 800, 600)
size = QSize(120, 160)
controller = MovementController(
    get_position=lambda: QPoint(position),
    get_pet_size=lambda: QSize(size),
    get_available_geometry=lambda: QRect(area),
    walk_speed=100_000,
    run_speed=100_000,
    minimum_duration=1,
)
controller.movement_position_changed.connect(lambda value: position.setX(value.x()))
controller.movement_position_changed.connect(lambda value: position.setY(value.y()))
controller.movement_finished.connect(lambda _mode, value: position.setX(value.x()))
controller.movement_finished.connect(lambda _mode, value: position.setY(value.y()))


def wait_for_finish() -> None:
    loop = QEventLoop()
    controller.movement_finished.connect(loop.quit)
    QTimer.singleShot(1000, loop.quit)
    loop.exec()


assert controller.clamp_target(QPoint(-10, 999), size, area) == QPoint(0, 440)

directions: list[str] = []
controller.direction_changed.connect(directions.append)
controller.move_to(QPoint(700, 200), "walk")
wait_for_finish()
assert position == QPoint(680, 200)
controller.move_to(QPoint(20, 200), "run")
wait_for_finish()
assert position == QPoint(20, 200)
assert "left" in directions

for index in range(50):
    target = QPoint(40 if index % 2 else 600, 200)
    controller.move_to(target)
    wait_for_finish()
assert position == QPoint(40, 200)

controller.move_to(QPoint(600, 200))
stop_loop = QEventLoop()
QTimer.singleShot(1, stop_loop.quit)
stop_loop.exec()
stopped = controller.stop()
assert not controller.is_moving()
assert area.contains(stopped)

print("screen_bounds=True")
print("direction_switch=True")
print("fifty_moves_no_drift=True")
print("stop_mid_movement=True")

