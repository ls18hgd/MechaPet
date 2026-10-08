"""Validated, path-safe character pack model for MechaPet V0.3."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PyQt6.QtGui import QImage


logger = logging.getLogger(__name__)

SUPPORTED_ANIMATIONS = frozenset(
    {
        "idle",
        "blink",
        "walk",
        "run",
        "talk",
        "wave",
        "happy",
        "curious",
        "thinking",
        "sad",
        "sleepy",
    }
)


class CharacterPackError(ValueError):
    """Raised when a character pack is unsafe or structurally invalid."""


@dataclass(frozen=True, slots=True)
class CanvasSpec:
    width: int
    height: int
    anchor_x: int
    anchor_y: int


@dataclass(frozen=True, slots=True)
class AnimationSpec:
    name: str
    directory: Path
    frames: tuple[Path, ...]
    fps: int
    loop: bool


@dataclass(frozen=True, slots=True)
class CharacterPack:
    root: Path
    id: str
    name: str
    version: int
    canvas: CanvasSpec
    animations: dict[str, AnimationSpec]
    fallback_animation: str
    portrait_path: Path | None
    persona_prompt_path: Path | None

    @classmethod
    def load(cls, root: Path) -> "CharacterPack":
        pack_root = root.resolve()
        manifest_path = pack_root / "manifest.json"
        if not manifest_path.is_file():
            raise CharacterPackError(f"缺少 manifest.json：{pack_root}")
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CharacterPackError(f"manifest.json 无法读取：{exc}") from exc
        if not isinstance(payload, dict):
            raise CharacterPackError("manifest 根节点必须是 JSON 对象")
        return cls._from_payload(pack_root, payload)

    @classmethod
    def _from_payload(cls, root: Path, data: dict[str, Any]) -> "CharacterPack":
        pack_id = _required_text(data, "id")
        display_name = _required_text(data, "name")
        version = _positive_int(data.get("version"), "version")

        canvas_data = data.get("canvas")
        if not isinstance(canvas_data, dict):
            raise CharacterPackError("canvas 必须是对象")
        canvas = CanvasSpec(
            width=_positive_int(canvas_data.get("width"), "canvas.width"),
            height=_positive_int(canvas_data.get("height"), "canvas.height"),
            anchor_x=_non_negative_int(canvas_data.get("anchor_x"), "canvas.anchor_x"),
            anchor_y=_non_negative_int(canvas_data.get("anchor_y"), "canvas.anchor_y"),
        )
        if canvas.anchor_x > canvas.width or canvas.anchor_y > canvas.height:
            raise CharacterPackError("脚底锚点必须位于角色画布范围内")

        animations_data = data.get("animations")
        if not isinstance(animations_data, dict) or not animations_data:
            raise CharacterPackError("animations 必须是非空对象")
        animations: dict[str, AnimationSpec] = {}
        for name, raw_spec in animations_data.items():
            if name not in SUPPORTED_ANIMATIONS:
                logger.warning("Ignoring unsupported animation %s in %s", name, pack_id)
                continue
            if not isinstance(raw_spec, dict):
                raise CharacterPackError(f"动画 {name} 必须是对象")
            directory = _safe_child(root, _required_text(raw_spec, "path"))
            if not directory.is_dir():
                raise CharacterPackError(f"动画目录不存在：{directory}")
            frames = tuple(sorted(directory.glob("*.png"), key=lambda item: item.name))
            if not frames:
                raise CharacterPackError(f"动画 {name} 没有 PNG 帧")
            fps = _positive_int(raw_spec.get("fps"), f"animations.{name}.fps")
            if fps > 60:
                raise CharacterPackError(f"动画 {name} 的 fps 不能超过 60")
            loop = raw_spec.get("loop")
            if not isinstance(loop, bool):
                raise CharacterPackError(f"动画 {name} 的 loop 必须是布尔值")
            _validate_frames(frames, canvas, name)
            animations[name] = AnimationSpec(name, directory, frames, fps, loop)

        fallback = data.get("fallback_animation", "idle")
        if not isinstance(fallback, str) or fallback not in animations:
            raise CharacterPackError("fallback_animation 必须指向已存在的动画")
        portrait = _optional_safe_file(root, data.get("portrait", "portrait.png"))
        persona = _optional_safe_file(root, data.get("persona_prompt"))
        return cls(
            root=root,
            id=pack_id,
            name=display_name,
            version=version,
            canvas=canvas,
            animations=animations,
            fallback_animation=fallback,
            portrait_path=portrait,
            persona_prompt_path=persona,
        )

    def get_animation(self, name: str) -> AnimationSpec:
        return self.animations.get(name, self.animations[self.fallback_animation])

    def has_animation(self, name: str) -> bool:
        return name in self.animations

    def read_persona_prompt(self) -> str:
        if self.persona_prompt_path is None:
            return ""
        return self.persona_prompt_path.read_text(encoding="utf-8").strip()


def _safe_child(root: Path, relative: str) -> Path:
    candidate_value = Path(relative)
    if candidate_value.is_absolute():
        raise CharacterPackError(f"角色包路径不能是绝对路径：{relative}")
    candidate = (root / candidate_value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise CharacterPackError(f"角色包路径越界：{relative}") from exc
    return candidate


def _optional_safe_file(root: Path, value: Any) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CharacterPackError("可选文件路径必须是非空字符串")
    path = _safe_child(root, value)
    return path if path.is_file() else None


def _validate_frames(
    frames: tuple[Path, ...], canvas: CanvasSpec, animation_name: str
) -> None:
    for frame in frames:
        image = QImage(str(frame))
        if image.isNull():
            raise CharacterPackError(f"无法读取动画帧：{frame}")
        if image.width() != canvas.width or image.height() != canvas.height:
            raise CharacterPackError(
                f"动画 {animation_name} 的帧尺寸不一致：{frame.name} "
                f"是 {image.width()}x{image.height()}，应为 {canvas.width}x{canvas.height}"
            )
        if not image.hasAlphaChannel():
            raise CharacterPackError(f"动画帧必须包含 Alpha 通道：{frame}")


def _required_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CharacterPackError(f"{key} 必须是非空字符串")
    return value.strip()


def _positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise CharacterPackError(f"{field} 必须是正整数")
    return value


def _non_negative_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CharacterPackError(f"{field} 必须是非负整数")
    return value
