"""State model for the desktop pet, independent from widget rendering."""

import logging
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal


logger = logging.getLogger(__name__)


class PetState(Enum):
    IDLE = "idle"
    HAPPY = "happy"
    CURIOUS = "curious"
    THINKING = "thinking"
    TALKING = "talking"
    SAD = "sad"
    SLEEPY = "sleepy"


class PetStateModel(QObject):
    """Own the current pet state and notify presentation code of changes."""

    state_changed = pyqtSignal(PetState)

    def __init__(self) -> None:
        super().__init__()
        self._state = PetState.IDLE

    def set_state(self, state: PetState | str) -> PetState:
        try:
            resolved = state if isinstance(state, PetState) else PetState(state)
        except ValueError:
            logger.warning("Unknown pet state %r; falling back to idle", state)
            resolved = PetState.IDLE
        if resolved != self._state:
            self._state = resolved
            self.state_changed.emit(resolved)
        return self._state

    def get_state(self) -> PetState:
        return self._state

    def restore_idle(self) -> None:
        self.set_state(PetState.IDLE)
