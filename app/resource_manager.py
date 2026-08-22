"""Cached state-aware asset loading for MechaPet."""

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from app.config import PROJECT_ROOT
from app.pet_state import PetState


logger = logging.getLogger(__name__)


class ResourceManager:
    """Load state sprites with a shared fallback and an in-memory cache."""

    def __init__(self, assets_root: Path | None = None, pet_height: int = 320) -> None:
        self.assets_root = assets_root or PROJECT_ROOT / "assets"
        self.pet_height = pet_height
        self._fallback_path = self.assets_root / "pet.png"
        self._state_root = self.assets_root / "pet"
        self._cache: dict[PetState, QPixmap] = {}
        self._fallback_pixmap: QPixmap | None = None

    def get_pet_pixmap(self, state: PetState | str) -> QPixmap:
        try:
            resolved = state if isinstance(state, PetState) else PetState(state)
        except ValueError:
            logger.warning("Unknown resource state %r; using idle", state)
            resolved = PetState.IDLE
        if resolved not in self._cache:
            self._cache[resolved] = self._load_state_pixmap(resolved)
        return self._cache[resolved]

    def clear_cache(self) -> None:
        self._cache.clear()
        self._fallback_pixmap = None

    def _load_state_pixmap(self, state: PetState) -> QPixmap:
        state_path = self._state_root / f"{state.value}.png"
        if not state_path.is_file():
            logger.info("State asset missing (%s); using pet.png", state_path.name)
            if self._fallback_pixmap is None:
                self._fallback_pixmap = self._load_scaled(self._fallback_path)
            return self._fallback_pixmap
        return self._load_scaled(state_path)

    def _load_scaled(self, path: Path) -> QPixmap:
        pixmap = QPixmap(str(path)) if path.is_file() else QPixmap()
        if pixmap.isNull():
            logger.error("Pet resource missing or invalid: %s", path)
            return pixmap
        return pixmap.scaledToHeight(
            self.pet_height,
            Qt.TransformationMode.SmoothTransformation,
        )
