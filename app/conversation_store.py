"""Persistent, atomic local conversation history for MechaPet V0.4."""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QStandardPaths


logger = logging.getLogger(__name__)
HISTORY_VERSION = 1
MAX_STORED_MESSAGES = 200


def default_history_path() -> Path:
    override = os.getenv("MECHAPET_HISTORY_PATH", "").strip()
    if override:
        return Path(override)
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data) / "MechaPet" / "conversation_history.json"
    root = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    return Path(root) / "conversation_history.json"


class ConversationStore:
    """Load and atomically save display history plus model context."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_history_path()

    def load(self) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        if not self.path.is_file():
            return [], []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("version") != HISTORY_VERSION:
                raise ValueError("unsupported history format")
            display = _validated_messages(
                payload.get("display_messages"), {"user", "assistant"}
            )
            context = _validated_messages(
                payload.get("context_messages"), {"user", "assistant"}
            )
            return display[-MAX_STORED_MESSAGES:], context[-MAX_STORED_MESSAGES:]
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Conversation history ignored: %s", exc)
            return [], []

    def save(
        self,
        display_messages: list[dict[str, str]],
        context_messages: list[dict[str, str]],
    ) -> bool:
        display = _validated_messages(display_messages, {"user", "assistant"})
        context = _validated_messages(context_messages, {"user", "assistant"})
        payload = {
            "version": HISTORY_VERSION,
            "display_messages": display[-MAX_STORED_MESSAGES:],
            "context_messages": context[-MAX_STORED_MESSAGES:],
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            encoded = json.dumps(payload, ensure_ascii=False, indent=2)
            temporary_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=self.path.parent,
                    prefix=f".{self.path.name}.",
                    suffix=".tmp",
                    delete=False,
                ) as output:
                    temporary_path = Path(output.name)
                    output.write(encoded)
                    output.flush()
                    os.fsync(output.fileno())
                try:
                    os.replace(temporary_path, self.path)
                except OSError as exc:
                    # Some managed Windows folders report WinError 17 even for
                    # siblings. Preserve reliable saving with a copy fallback.
                    if getattr(exc, "winerror", None) != 17:
                        raise
                    shutil.copyfile(temporary_path, self.path)
            finally:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)
            return True
        except (OSError, ValueError) as exc:
            logger.warning("Conversation history could not be saved: %s", exc)
            return False

    def clear(self) -> bool:
        try:
            self.path.unlink(missing_ok=True)
            return True
        except OSError as exc:
            logger.warning("Conversation history could not be cleared: %s", exc)
            return False


def _validated_messages(value: Any, roles: set[str]) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("message history must be a list")
    result: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("history message must be an object")
        role = item.get("role")
        content = item.get("content")
        if role not in roles or not isinstance(content, str) or not content.strip():
            raise ValueError("history message contains invalid role or content")
        result.append({"role": role, "content": content})
    return result
