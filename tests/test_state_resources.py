"""Milestone 1 checks for state transitions and asset fallback caching."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import QApplication

from app.pet_state import PetState, PetStateModel
from app.resource_manager import ResourceManager


def main() -> None:
    app = QApplication.instance() or QApplication([])
    model = PetStateModel()
    observed: list[PetState] = []
    model.state_changed.connect(observed.append)
    for state in PetState:
        assert model.set_state(state) is state
        assert model.get_state() is state
    model.restore_idle()
    assert model.get_state() is PetState.IDLE
    assert model.set_state("invalid") is PetState.IDLE

    resources = ResourceManager()
    idle = resources.get_pet_pixmap(PetState.IDLE)
    assert not idle.isNull()
    assert idle.hasAlphaChannel()
    assert resources.get_pet_pixmap(PetState.HAPPY).cacheKey() == idle.cacheKey()
    assert resources.get_pet_pixmap(PetState.HAPPY).cacheKey() == resources.get_pet_pixmap(PetState.HAPPY).cacheKey()
    print(f"state_transitions={len(observed)}")
    print(f"fallback_size={idle.width()}x{idle.height()}")
    print("resource_cache=True")
    app.processEvents()


if __name__ == "__main__":
    main()
