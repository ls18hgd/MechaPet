"""Coordinate pet state and lightweight actions without owning UI layout."""

import random
import time
from collections.abc import Callable

from PyQt6.QtCore import QObject, QPoint, QTimer

from app.action_controller import ActionController
from app.ai_response import AIResponse
from app.behavior_controller import BehaviorController
from app.character_manager import CharacterManager
from app.movement_controller import MovementController
from app.pet_state import PetState, PetStateModel
from app.speech_bubble import SpeechBubble
from app.sprite_animator import SpriteAnimator


class PetController(QObject):
    """Application-level coordinator between pet behavior and presentation."""

    CLICK_INTERACTIONS = (
        (PetState.HAPPY, "bounce"),
        (PetState.CURIOUS, "nod"),
        (PetState.HAPPY, "wave"),
    )
    IDLE_INTERACTIONS = (
        (PetState.CURIOUS, "nod"),
        (PetState.HAPPY, "wave"),
        (PetState.SLEEPY, "nod"),
        (PetState.IDLE, "shake"),
    )

    def __init__(
        self,
        apply_pixmap: Callable,
        apply_offset: Callable,
        show_chat: Callable[[], None],
        pet_geometry: Callable,
        get_movement_position: Callable,
        apply_movement_position: Callable,
        commit_movement_position: Callable,
        get_pet_size: Callable,
        get_available_geometry: Callable,
    ) -> None:
        super().__init__()
        self.state = PetStateModel()
        self.characters = CharacterManager()
        self.sprite_animator = SpriteAnimator()
        self.actions = ActionController()
        self.movement = MovementController(
            get_position=get_movement_position,
            get_pet_size=get_pet_size,
            get_available_geometry=get_available_geometry,
        )
        self.speech_bubble = SpeechBubble()
        self._apply_pixmap = apply_pixmap
        self._show_chat = show_chat
        self._pet_geometry = pet_geometry
        self._get_movement_position = get_movement_position
        self._get_pet_size = get_pet_size
        self._get_available_geometry = get_available_geometry
        self._last_interaction_time = time.monotonic()
        self._shutting_down = False
        self.behavior = BehaviorController(
            can_run=self._can_run_idle_behavior,
            perform=self._perform_idle_behavior,
        )

        self.state.state_changed.connect(self._on_state_changed)
        self.characters.character_changed.connect(self._on_character_changed)
        self.sprite_animator.frame_changed.connect(apply_pixmap)
        self.actions.offset_changed.connect(apply_offset)
        self.actions.action_started.connect(self._on_action_started)
        self.actions.action_finished.connect(self._on_action_finished)
        self.movement.movement_position_changed.connect(apply_movement_position)
        self.movement.movement_started.connect(self._on_movement_started)
        self.movement.movement_finished.connect(
            lambda _mode, position: self._finish_movement(position, commit_movement_position)
        )
        self.movement.movement_stopped.connect(commit_movement_position)
        self.movement.direction_changed.connect(self.sprite_animator.set_direction)

    @property
    def last_interaction_time(self) -> float:
        return self._last_interaction_time

    def start(self) -> None:
        self.sprite_animator.set_character(self.characters.current)
        self._on_state_changed(self.state.get_state())
        self.actions.start_idle_breathing()
        self.behavior.start()

    def mark_interaction(self) -> None:
        self._last_interaction_time = time.monotonic()
        self.behavior.reset_after_interaction()

    def handle_click(self) -> None:
        self.mark_interaction()
        if self.state.get_state() is PetState.THINKING:
            return
        state, action = random.choice(self.CLICK_INTERACTIONS)
        self.state.set_state(state)
        self.actions.play(action)

    def handle_double_click(self) -> None:
        self.mark_interaction()
        self._show_chat()

    def handle_drag_started(self) -> None:
        self.mark_interaction()
        self.movement.stop()
        self.actions.pause_for_drag()

    def handle_drag_finished(self) -> None:
        self.mark_interaction()
        self.actions.resume_after_drag(resume_idle=False)
        if self.state.get_state() is PetState.THINKING:
            self.actions.start_thinking()
        else:
            self.state.restore_idle()
            self.actions.start_idle_breathing()

    def handle_pet_moved(self, geometry) -> None:
        self.speech_bubble.follow_pet(geometry)

    def show_speech(self, text: str, pet_geometry) -> None:
        self.speech_bubble.show_message(text, pet_geometry)

    def handle_ai_started(self) -> None:
        self.mark_interaction()
        self.state.set_state(PetState.THINKING)
        self.actions.start_thinking()

    def handle_ai_response(self, response: AIResponse) -> None:
        self.mark_interaction()
        self.actions.stop_action()
        self.state.set_state(response.emotion)
        self.show_speech(response.text, self._pet_geometry())
        if response.action == "none":
            self.actions.start_idle_breathing()
            QTimer.singleShot(1200, self._restore_idle_if_available)
        else:
            self.actions.play(response.action)

    def handle_ai_error(self, error: str) -> None:
        del error
        self.mark_interaction()
        self.actions.stop_action()
        self.state.restore_idle()
        self.actions.start_idle_breathing()

    def prepare_to_quit(self) -> None:
        self._shutting_down = True
        self.behavior.stop()
        self.movement.stop(emit_signal=False)
        self.actions.stop_idle_breathing()
        self.actions.stop_action()
        self.sprite_animator.stop()
        self.speech_bubble.hide()

    def _on_state_changed(self, state: PetState) -> None:
        self.sprite_animator.play(state.value)

    def _on_character_changed(self, pack) -> None:
        self.sprite_animator.set_character(pack)
        self._on_state_changed(self.state.get_state())

    def _on_action_started(self, action: str) -> None:
        pack = self.characters.current
        if pack.has_animation(action):
            self.sprite_animator.play(action)

    def _on_action_finished(self, action: str) -> None:
        del action
        if self._shutting_down or self.state.get_state() is PetState.THINKING:
            return
        self.state.restore_idle()
        self.actions.start_idle_breathing()

    def _restore_idle_if_available(self) -> None:
        if not self._shutting_down and self.state.get_state() is not PetState.THINKING:
            self.state.restore_idle()

    def _can_run_idle_behavior(self) -> bool:
        return (
            not self._shutting_down
            and not self.actions.is_dragging()
            and not self.actions.is_animating()
            and not self.movement.is_moving()
            and self.state.get_state() is PetState.IDLE
        )

    def _perform_idle_behavior(self) -> None:
        if random.random() < 0.35:
            self._start_random_movement()
            return
        state, action = random.choice(self.IDLE_INTERACTIONS)
        self.state.set_state(state)
        self.actions.play(action)

    def walk_to(self, target, run: bool = False) -> None:
        self.mark_interaction()
        self.actions.stop_idle_breathing()
        self.actions.stop_action()
        self.state.restore_idle()
        self.movement.move_to(target, "run" if run else "walk")

    def _finish_movement(self, position, commit: Callable) -> None:
        commit(position)
        if self._shutting_down:
            return
        self.state.restore_idle()
        self.sprite_animator.play("idle")
        self.actions.start_idle_breathing()

    def _on_movement_started(self, mode: str) -> None:
        self.sprite_animator.play(mode)

    def _start_random_movement(self) -> None:
        area = self._get_available_geometry()
        size = self._get_pet_size()
        current = self._get_movement_position()
        min_x = area.left()
        max_x = max(min_x, area.right() - size.width() + 1)
        distance = random.randint(100, 320)
        direction = random.choice((-1, 1))
        target_x = min(max(current.x() + direction * distance, min_x), max_x)
        self.walk_to(QPoint(target_x, current.y()), run=random.random() < 0.2)
