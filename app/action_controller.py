"""Non-blocking lightweight PNG animation controller."""

import logging

from PyQt6.QtCore import (
    QEasingCurve,
    QObject,
    QPoint,
    QPropertyAnimation,
    pyqtProperty,
    pyqtSignal,
)

from app.config import (
    CLICK_ANIMATION_DURATION,
    IDLE_ANIMATION_DURATION,
    PET_ANIMATION_OFFSET,
)


logger = logging.getLogger(__name__)
VALID_ACTIONS = frozenset({"none", "bounce", "nod", "shake", "wave"})


class ActionController(QObject):
    """Produce animation offsets without ever owning the window position."""

    offset_changed = pyqtSignal(QPoint)
    action_started = pyqtSignal(str)
    action_finished = pyqtSignal(str)

    def __init__(
        self,
        action_duration: int = CLICK_ANIMATION_DURATION,
        idle_duration: int = IDLE_ANIMATION_DURATION,
        offset: int = PET_ANIMATION_OFFSET,
    ) -> None:
        super().__init__()
        self.action_duration = action_duration
        self.idle_duration = idle_duration
        self.offset = offset
        self._animation_offset = QPoint()
        self._active_animation: QPropertyAnimation | None = None
        self._idle_animation: QPropertyAnimation | None = None
        self._active_action: str | None = None
        self._idle_requested = False
        self._dragging = False

    def _get_animation_offset(self) -> QPoint:
        return self._animation_offset

    def _set_animation_offset(self, value: QPoint) -> None:
        if value != self._animation_offset:
            self._animation_offset = value
            self.offset_changed.emit(QPoint(value))

    animationOffset = pyqtProperty(  # noqa: N815
        QPoint, fget=_get_animation_offset, fset=_set_animation_offset
    )

    def current_offset(self) -> QPoint:
        return QPoint(self._animation_offset)

    def play(self, action: str) -> bool:
        """Play one finite action and restore an exact zero offset afterward."""
        if action == "none":
            self.stop_action()
            self.action_finished.emit(action)
            return True
        if action not in VALID_ACTIONS:
            logger.warning("Unknown action %r", action)
            return False
        if self._dragging:
            return False

        self._stop_idle_animation(reset=False)
        self.stop_action()
        try:
            animation = self._build_action_animation(action)
        except Exception:
            logger.exception("Animation creation failed for action %s", action)
            self._set_animation_offset(QPoint())
            return False
        self._active_animation = animation
        self._active_action = action
        animation.finished.connect(self._finish_action)
        self.action_started.emit(action)
        animation.start()
        return True

    def start_idle_breathing(self) -> None:
        self._idle_requested = True
        if self._dragging or self._active_animation is not None:
            return
        if self._idle_animation is not None:
            return
        animation = QPropertyAnimation(self, b"animationOffset", self)
        animation.setDuration(self.idle_duration)
        animation.setLoopCount(-1)
        animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        animation.setKeyValueAt(0.0, QPoint())
        animation.setKeyValueAt(0.5, QPoint(0, -2))
        animation.setKeyValueAt(1.0, QPoint())
        self._idle_animation = animation
        animation.start()

    def stop_idle_breathing(self) -> None:
        self._idle_requested = False
        self._stop_idle_animation(reset=self._active_animation is None)

    def start_thinking(self) -> None:
        if self._dragging:
            return
        self._idle_requested = False
        self._stop_idle_animation(reset=False)
        self.stop_action()
        animation = QPropertyAnimation(self, b"animationOffset", self)
        animation.setDuration(1800)
        animation.setLoopCount(-1)
        animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        animation.setKeyValueAt(0.0, QPoint())
        animation.setKeyValueAt(0.25, QPoint(-3, -1))
        animation.setKeyValueAt(0.5, QPoint())
        animation.setKeyValueAt(0.75, QPoint(3, -1))
        animation.setKeyValueAt(1.0, QPoint())
        self._active_animation = animation
        self._active_action = "thinking"
        self.action_started.emit("thinking")
        animation.start()

    def stop_action(self) -> None:
        animation = self._active_animation
        self._active_animation = None
        self._active_action = None
        if animation is not None:
            animation.stop()
            animation.deleteLater()
        self._set_animation_offset(QPoint())

    def pause_for_drag(self) -> None:
        self._dragging = True
        self._stop_idle_animation(reset=False)
        self.stop_action()

    def resume_after_drag(self, resume_idle: bool = True) -> None:
        self._dragging = False
        self._idle_requested = resume_idle
        if resume_idle:
            self.start_idle_breathing()

    def is_animating(self) -> bool:
        return self._active_animation is not None

    def is_dragging(self) -> bool:
        return self._dragging

    def _build_action_animation(self, action: str) -> QPropertyAnimation:
        animation = QPropertyAnimation(self, b"animationOffset", self)
        animation.setDuration(self.action_duration)
        animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        o = self.offset
        keyframes: dict[float, QPoint]
        if action == "bounce":
            keyframes = {
                0.0: QPoint(), 0.25: QPoint(0, -o),
                0.5: QPoint(), 0.72: QPoint(0, -(o // 2)), 1.0: QPoint(),
            }
        elif action == "nod":
            keyframes = {
                0.0: QPoint(), 0.3: QPoint(0, o // 2),
                0.55: QPoint(0, -2), 0.78: QPoint(0, o // 3), 1.0: QPoint(),
            }
        elif action == "shake":
            keyframes = {
                0.0: QPoint(), 0.2: QPoint(-o, 0), 0.4: QPoint(o, 0),
                0.6: QPoint(-o, 0), 0.8: QPoint(o // 2, 0), 1.0: QPoint(),
            }
        else:  # wave: a small asymmetric sway with a tiny lift
            keyframes = {
                0.0: QPoint(), 0.2: QPoint(-o // 2, -2),
                0.45: QPoint(o, -3), 0.7: QPoint(-o // 2, -1), 1.0: QPoint(),
            }
        for progress, value in keyframes.items():
            animation.setKeyValueAt(progress, value)
        return animation

    def _finish_action(self) -> None:
        action = self._active_action or "none"
        animation = self._active_animation
        self._active_animation = None
        self._active_action = None
        self._set_animation_offset(QPoint())
        if animation is not None:
            animation.deleteLater()
        self.action_finished.emit(action)
        if self._idle_requested and not self._dragging:
            self.start_idle_breathing()

    def _stop_idle_animation(self, reset: bool) -> None:
        animation = self._idle_animation
        self._idle_animation = None
        if animation is not None:
            animation.stop()
            animation.deleteLater()
        if reset:
            self._set_animation_offset(QPoint())
