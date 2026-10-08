"""V0.4 persistence checks for UI history and DeepSeek context."""

import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtWidgets import QApplication

from app.ai_client import AIClient
from app.chat_window import ChatWindow
from app.conversation_store import ConversationStore, MAX_STORED_MESSAGES


app = QApplication.instance() or QApplication(sys.argv)
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "history.json"
    store = ConversationStore(path)
    display = [
        {"role": "user", "content": "请记住数字 9527"},
        {"role": "assistant", "content": "好的，我记住了。"},
    ]
    context = [
        {"role": "user", "content": "请记住数字 9527"},
        {
            "role": "assistant",
            "content": '{"emotion":"idle","action":"none","text":"好的，我记住了。"}',
        },
    ]
    assert store.save(display, context)
    assert store.load() == (display, context)

    first_client = AIClient()
    first_window = ChatWindow(first_client, history_store=store)
    assert first_window._display_messages == display
    assert first_client.conversation_history() == context

    first_window._display_messages.append(
        {"role": "user", "content": "刚才的数字是什么？"}
    )
    first_client.load_history(
        [*context, {"role": "user", "content": "刚才的数字是什么？"}]
    )
    first_window._save_history()

    restarted_client = AIClient()
    restarted_window = ChatWindow(restarted_client, history_store=store)
    assert restarted_window._display_messages[-1]["content"] == "刚才的数字是什么？"
    assert restarted_client.conversation_history()[-1]["content"] == "刚才的数字是什么？"

    many = [
        {"role": "user", "content": f"message-{index}"}
        for index in range(MAX_STORED_MESSAGES + 20)
    ]
    assert store.save(many, many)
    limited_display, limited_context = store.load()
    assert len(limited_display) == MAX_STORED_MESSAGES
    assert len(limited_context) == MAX_STORED_MESSAGES

    path.write_text("{broken", encoding="utf-8")
    assert store.load() == ([], [])
    assert store.clear() and not path.exists()

print("atomic_round_trip=True")
print("restart_restores_display=True")
print("restart_restores_ai_context=True")
print("history_limit=True")
print("corrupt_file_safe=True")
print("clear_history=True")

