"""Milestone 6 local test of threaded AI-to-pet UI coordination."""

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["MECHAPET_HISTORY_PATH"] = str(
    Path(tempfile.gettempdir()) / f"mechapet-ai-test-{os.getpid()}.json"
)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QEventLoop, QThread, QTimer
from PyQt6.QtWidgets import QApplication

from app.ai_client import AIClientError
from app.ai_response import AIResponse
from app.pet_state import PetState
from app.pet_window import PetWindow


class SuccessfulClient:
    def send_message(self, message: str) -> AIResponse:
        assert message == "我今天有点开心"
        time.sleep(0.15)
        return AIResponse("happy", "bounce", "那很好呀，今天也要 **开心**。")


class FailingClient:
    def send_message(self, message: str) -> AIResponse:
        del message
        time.sleep(0.05)
        raise AIClientError("模拟网络错误")


def wait_until_ready(chat, timeout: int = 3000) -> int:
    loop = QEventLoop()
    heartbeats = 0

    def poll() -> None:
        nonlocal heartbeats
        heartbeats += 1
        if not chat._busy:
            loop.quit()

    timer = QTimer()
    timer.timeout.connect(poll)
    timer.start(20)
    QTimer.singleShot(timeout, loop.quit)
    loop.exec()
    timer.stop()
    assert not chat._busy
    return heartbeats


def wait(milliseconds: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    pet = PetWindow()
    pet.show()
    chat = pet._chat_window
    gui_thread_results: list[bool] = []
    chat.response_received.connect(
        lambda _response: gui_thread_results.append(
            QThread.currentThread() is app.thread()
        )
    )

    chat._ai_client = SuccessfulClient()
    chat.input.setText("我今天有点开心")
    chat.send_current_message()
    assert pet._controller.state.get_state() is PetState.THINKING
    assert pet._controller.actions.is_animating()
    heartbeats = wait_until_ready(chat)
    assert heartbeats > 1
    assert gui_thread_results == [True]
    assert pet._controller.state.get_state() is PetState.HAPPY
    assert pet._controller.speech_bubble.isVisible()
    assert "**开心**" not in chat.history.toPlainText()
    wait(1000)
    assert pet._controller.state.get_state() is PetState.IDLE
    print(f"success_gui_heartbeats={heartbeats}")
    print("thinking_to_happy_bounce_bubble_idle=True")
    print("all_ui_updates_on_gui_thread=True")

    pet._controller.speech_bubble.hide()
    chat._ai_client = FailingClient()
    chat.input.setText("触发错误")
    chat.send_current_message()
    assert pet._controller.state.get_state() is PetState.THINKING
    wait_until_ready(chat)
    assert pet._controller.state.get_state() is PetState.IDLE
    assert "模拟网络错误" in chat.history.toPlainText()
    print("error_restores_idle=True")
    app.quit()


if __name__ == "__main__":
    main()
