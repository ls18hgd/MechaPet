"""Low-frequency autonomous idle behavior scheduler."""

import random
from collections.abc import Callable

from PyQt6.QtCore import QObject, QTimer

from app.config import IDLE_BEHAVIOR_MAX_SECONDS, IDLE_BEHAVIOR_MIN_SECONDS


class BehaviorController(QObject):
    """Schedule occasional behavior while respecting a controller safety gate."""

    def __init__(
        self,
        can_run: Callable[[], bool],
        perform: Callable[[], None],
        min_seconds: float = IDLE_BEHAVIOR_MIN_SECONDS,
        max_seconds: float = IDLE_BEHAVIOR_MAX_SECONDS,
    ) -> None:
        super().__init__()
        self._can_run = can_run
        self._perform = perform
        self.min_seconds = min_seconds
        self.max_seconds = max_seconds
        self._running = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

    def start(self) -> None:
        self._running = True
        self._schedule_next()

    def stop(self) -> None:
        self._running = False
        self._timer.stop()

    def reset_after_interaction(self) -> None:
        if self._running:
            self._schedule_next()

    def _on_timeout(self) -> None:
        if not self._running:
            return
        if self._can_run():
            self._perform()
        self._schedule_next()

    def _schedule_next(self) -> None:
        self._timer.stop()
        if not self._running:
            return
        lower = min(self.min_seconds, self.max_seconds)
        upper = max(self.min_seconds, self.max_seconds)
        delay_ms = max(1, round(random.uniform(lower, upper) * 1000))
        self._timer.start(delay_ms)
