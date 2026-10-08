"""GUI-thread PNG sequence player for validated character packs."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QTransform

from app.character_pack import AnimationSpec, CharacterPack


logger = logging.getLogger(__name__)


class SpriteAnimator(QObject):
    animation_started = pyqtSignal(str)
    frame_changed = pyqtSignal(QPixmap)
    animation_finished = pyqtSignal(str)

    def __init__(self, target_height: int = 320) -> None:
        super().__init__()
        self.target_height = target_height
        self._pack: CharacterPack | None = None
        self._spec: AnimationSpec | None = None
        self._requested_name = ""
        self._frame_index = 0
        self._direction = "right"
        self._cache: dict[tuple[str, str], tuple[QPixmap, ...]] = {}
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    @property
    def current_animation(self) -> str:
        return self._requested_name

    @property
    def direction(self) -> str:
        return self._direction

    def set_character(self, pack: CharacterPack) -> None:
        self.stop()
        self._pack = pack
        self._cache.clear()

    def set_direction(self, direction: str) -> None:
        if direction not in {"left", "right"}:
            raise ValueError("direction 必须是 left 或 right")
        if direction == self._direction:
            return
        self._direction = direction
        if self._spec is not None:
            self._emit_current_frame()

    def play(self, name: str, restart: bool = True) -> bool:
        self._assert_gui_thread()
        if self._pack is None:
            logger.warning("Cannot play animation without a character pack")
            return False
        if not restart and self._timer.isActive() and name == self._requested_name:
            return True
        spec = self._pack.get_animation(name)
        frames = self._load_frames(spec)
        if not frames:
            logger.error("Animation %s contains no loadable frames", spec.name)
            return False
        self._timer.stop()
        self._spec = spec
        self._requested_name = name
        self._frame_index = 0
        self.animation_started.emit(name)
        self._emit_current_frame()
        self._timer.start(max(1, round(1000 / spec.fps)))
        return True

    def stop(self) -> None:
        self._timer.stop()
        self._spec = None
        self._requested_name = ""
        self._frame_index = 0

    def pause(self) -> None:
        self._timer.stop()

    def resume(self) -> None:
        if self._spec is not None and not self._timer.isActive():
            self._timer.start(max(1, round(1000 / self._spec.fps)))

    def is_playing(self) -> bool:
        return self._timer.isActive()

    def _advance(self) -> None:
        if self._spec is None:
            self._timer.stop()
            return
        frames = self._load_frames(self._spec)
        next_index = self._frame_index + 1
        if next_index >= len(frames):
            if self._spec.loop:
                next_index = 0
            else:
                name = self._requested_name
                self._timer.stop()
                self._frame_index = len(frames) - 1
                self.animation_finished.emit(name)
                return
        self._frame_index = next_index
        self._emit_current_frame()

    def _emit_current_frame(self) -> None:
        if self._spec is None:
            return
        frames = self._load_frames(self._spec)
        pixmap = frames[self._frame_index]
        if self._direction == "left":
            pixmap = pixmap.transformed(QTransform().scale(-1, 1))
        self.frame_changed.emit(pixmap)

    def _load_frames(self, spec: AnimationSpec) -> tuple[QPixmap, ...]:
        if self._pack is None:
            return ()
        key = (self._pack.id, spec.name)
        if key not in self._cache:
            frames: list[QPixmap] = []
            for path in spec.frames:
                source = QPixmap(str(path))
                if source.isNull():
                    logger.error("Failed to load sprite frame %s", path)
                    continue
                frames.append(source.scaledToHeight(self.target_height))
            self._cache[key] = tuple(frames)
        return self._cache[key]

    def _assert_gui_thread(self) -> None:
        if QThread.currentThread() is not self.thread():
            raise RuntimeError("SpriteAnimator 必须在其 GUI 线程中调用")
