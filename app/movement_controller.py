"""Screen-bounded base movement for walking and running desktop pets."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable

from PyQt6.QtCore import (
    QEasingCurve,
    QObject,
    QPoint,
    QRect,
    QSize,
    QPropertyAnimation,
    pyqtProperty,
    pyqtSignal,
)

from app.config import (
    MOVEMENT_MIN_DURATION,
    RUN_SPEED_PIXELS_PER_SECOND,
    WALK_SPEED_PIXELS_PER_SECOND,
)


logger = logging.getLogger(__name__)


class MovementController(QObject):
    movement_position_changed = pyqtSignal(QPoint)
    movement_started = pyqtSignal(str)
    movement_finished = pyqtSignal(str, QPoint)
    movement_stopped = pyqtSignal(QPoint)
    direction_changed = pyqtSignal(str)

    def __init__(
        self,
        get_position: Callable[[], QPoint],
        get_pet_size: Callable[[], QSize],
        get_available_geometry: Callable[[], QRect],
        walk_speed: int = WALK_SPEED_PIXELS_PER_SECOND,
        run_speed: int = RUN_SPEED_PIXELS_PER_SECOND,
        minimum_duration: int = MOVEMENT_MIN_DURATION,
    ) -> None:
        super().__init__()
        self._get_position = get_position
        self._get_pet_size = get_pet_size
        self._get_available_geometry = get_available_geometry
        self.walk_speed = walk_speed
        self.run_speed = run_speed
        self.minimum_duration = minimum_duration
        self._movement_position = QPoint()
        self._animation: QPropertyAnimation | None = None
        self._mode = ""
        self._direction = "right"

    def _get_movement_position(self) -> QPoint:
        return QPoint(self._movement_position)

    def _set_movement_position(self, value: QPoint) -> None:
        if value != self._movement_position:
            self._movement_position = QPoint(value)
            self.movement_position_changed.emit(QPoint(value))

    movementPosition = pyqtProperty(  # noqa: N815
        QPoint, fget=_get_movement_position, fset=_set_movement_position
    )

    @property
    def direction(self) -> str:
        return self._direction

    def is_moving(self) -> bool:
        return self._animation is not None

    def move_to(self, target: QPoint, mode: str = "walk") -> QPoint:
        if mode not in {"walk", "run"}:
            raise ValueError("mode 必须是 walk 或 run")
        self.stop(emit_signal=False)
        start = QPoint(self._get_position())
        bounded = self.clamp_target(
            target,
            self._get_pet_size(),
            self._get_available_geometry(),
        )
        self._movement_position = QPoint(start)
        if bounded.x() != start.x():
            direction = "right" if bounded.x() > start.x() else "left"
            if direction != self._direction:
                self._direction = direction
                self.direction_changed.emit(direction)
        if bounded == start:
            self.movement_finished.emit(mode, bounded)
            return bounded

        distance = math.hypot(bounded.x() - start.x(), bounded.y() - start.y())
        speed = self.run_speed if mode == "run" else self.walk_speed
        duration = max(self.minimum_duration, round(distance / max(1, speed) * 1000))
        animation = QPropertyAnimation(self, b"movementPosition", self)
        animation.setStartValue(start)
        animation.setEndValue(bounded)
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        animation.finished.connect(self._finish)
        self._animation = animation
        self._mode = mode
        self.movement_started.emit(mode)
        animation.start()
        return bounded

    def stop(self, emit_signal: bool = True) -> QPoint:
        animation = self._animation
        self._animation = None
        self._mode = ""
        if animation is not None:
            animation.stop()
            animation.deleteLater()
        current = (
            QPoint(self._movement_position)
            if animation is not None
            else QPoint(self._get_position())
        )
        if emit_signal and animation is not None:
            self.movement_stopped.emit(current)
        return current

    def clamp_target(self, target: QPoint, pet_size: QSize, area: QRect) -> QPoint:
        max_x = max(area.left(), area.right() - pet_size.width() + 1)
        max_y = max(area.top(), area.bottom() - pet_size.height() + 1)
        return QPoint(
            min(max(target.x(), area.left()), max_x),
            min(max(target.y(), area.top()), max_y),
        )

    def _finish(self) -> None:
        animation = self._animation
        mode = self._mode or "walk"
        final_position = QPoint(self._movement_position)
        self._animation = None
        self._mode = ""
        if animation is not None:
            animation.deleteLater()
        self.movement_finished.emit(mode, final_position)
