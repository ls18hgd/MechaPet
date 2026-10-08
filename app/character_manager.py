"""Discover, select, persist, and reload MechaPet character packs."""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QObject, QSettings, pyqtSignal

from app.character_pack import CharacterPack, CharacterPackError
from app.config import PROJECT_ROOT


logger = logging.getLogger(__name__)


class CharacterManager(QObject):
    character_changed = pyqtSignal(object)
    characters_reloaded = pyqtSignal()

    def __init__(
        self,
        characters_root: Path | None = None,
        settings: QSettings | None = None,
    ) -> None:
        super().__init__()
        self.characters_root = characters_root or PROJECT_ROOT / "characters"
        self.settings = settings or QSettings("MechaPet", "MechaPet")
        self._packs: dict[str, CharacterPack] = {}
        self._current_id = ""
        self.reload()

    def reload(self) -> None:
        discovered: dict[str, CharacterPack] = {}
        if self.characters_root.is_dir():
            for directory in sorted(self.characters_root.iterdir()):
                if not directory.is_dir():
                    continue
                try:
                    pack = CharacterPack.load(directory)
                except CharacterPackError as exc:
                    logger.warning("Skipping invalid character pack %s: %s", directory, exc)
                    continue
                if pack.id in discovered:
                    logger.warning("Skipping duplicate character id %s", pack.id)
                    continue
                discovered[pack.id] = pack
        if not discovered:
            raise CharacterPackError(f"没有可用角色包：{self.characters_root}")
        self._packs = discovered
        preferred = str(self.settings.value("character/current_id", "default"))
        selected = preferred if preferred in discovered else next(iter(discovered))
        changed = selected != self._current_id
        self._current_id = selected
        self.characters_reloaded.emit()
        if changed:
            self.character_changed.emit(self.current)

    @property
    def current(self) -> CharacterPack:
        return self._packs[self._current_id]

    @property
    def current_id(self) -> str:
        return self._current_id

    def available(self) -> tuple[CharacterPack, ...]:
        return tuple(self._packs.values())

    def select(self, character_id: str) -> CharacterPack:
        if character_id not in self._packs:
            raise CharacterPackError(f"未知角色：{character_id}")
        if character_id != self._current_id:
            self._current_id = character_id
            self.settings.setValue("character/current_id", character_id)
            self.settings.sync()
            self.character_changed.emit(self.current)
        return self.current
