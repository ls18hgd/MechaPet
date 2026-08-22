"""Validated structured response returned by the desktop-pet model."""

import json
import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)
ALLOWED_EMOTIONS = frozenset({"idle", "happy", "curious", "sad", "sleepy"})
ALLOWED_ACTIONS = frozenset({"none", "bounce", "nod", "shake", "wave"})


@dataclass(frozen=True, slots=True)
class AIResponse:
    emotion: str
    action: str
    text: str


def parse_ai_response(raw_text: str) -> AIResponse:
    """Parse the first JSON object in a model reply with safe field fallbacks."""
    original = raw_text.strip()
    payload = _extract_json_object(original)
    if payload is None:
        logger.warning("AI JSON parse failed; using original text")
        return AIResponse("idle", "none", original)

    emotion = payload.get("emotion", "idle")
    if not isinstance(emotion, str) or emotion not in ALLOWED_EMOTIONS:
        logger.warning("Unknown AI emotion %r; using idle", emotion)
        emotion = "idle"

    action = payload.get("action", "none")
    if not isinstance(action, str) or action not in ALLOWED_ACTIONS:
        logger.warning("Unknown AI action %r; using none", action)
        action = "none"

    text = payload.get("text", "")
    if not isinstance(text, str) or not text.strip():
        logger.warning("AI JSON text missing or empty; using original text")
        text = original
    else:
        text = text.strip()
    return AIResponse(emotion, action, text)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None
