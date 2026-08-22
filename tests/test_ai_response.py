"""Milestone 5 parser tests for normal and malformed model output."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai_response import AIResponse, parse_ai_response


CASES = {
    "normal": (
        '{"emotion":"happy","action":"bounce","text":"今天很好呀"}',
        AIResponse("happy", "bounce", "今天很好呀"),
    ),
    "markdown_fence": (
        '```json\n{"emotion":"curious","action":"nod","text":"让我想想"}\n```',
        AIResponse("curious", "nod", "让我想想"),
    ),
    "surrounding_text": (
        '这是结果：\n{"emotion":"sad","action":"shake","text":"抱抱你"}\n结束',
        AIResponse("sad", "shake", "抱抱你"),
    ),
    "missing_fields": (
        '{"text":"字段不全也没关系"}',
        AIResponse("idle", "none", "字段不全也没关系"),
    ),
    "invalid_values": (
        '{"emotion":"excited","action":"dance","text":"仍可显示"}',
        AIResponse("idle", "none", "仍可显示"),
    ),
    "empty_text": (
        '{"emotion":"happy","action":"wave","text":""}',
        AIResponse(
            "happy",
            "wave",
            '{"emotion":"happy","action":"wave","text":""}',
        ),
    ),
    "not_json": (
        "这是一条普通回复 **仍应显示**",
        AIResponse("idle", "none", "这是一条普通回复 **仍应显示**"),
    ),
}


def main() -> None:
    for name, (raw, expected) in CASES.items():
        actual = parse_ai_response(raw)
        assert actual == expected, (name, actual, expected)
        print(f"{name}=True")


if __name__ == "__main__":
    main()
