"""Small DeepSeek chat client with in-memory conversation context."""

import logging
from typing import Any

import requests

from app.config import AppConfig, config
from app.ai_response import AIResponse, parse_ai_response


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "你是 MechaPet，一个友好、聪明、自然、有轻微可爱感的桌面 AI 宠物。"
    "你会自然地陪伴用户，优先使用中文回答。与用户进行普通日常对话时，"
    "优先使用自然、简洁、口语化的文本。不要为了强调而频繁使用 Markdown，"
    "不要每一句话都加粗关键词。只有在确实有必要时才使用 Markdown，例如："
    "用户要求列步骤、询问代码、需要列表或其他结构化内容，或者某个关键词"
    "确实需要突出显示。普通聊天尽量不要大量使用粗体、标题、多层列表和代码块。"
    "整体风格应该更像一个自然的桌面伙伴，而不是一份技术文档。"
    "Markdown 并未被禁止；当它能让回答更清楚时，可以合理使用。"
    "每次回复需要同时决定当前情绪、一个轻量动作和实际回答，并且只输出一个"
    "合法 JSON 对象，格式为："
    '{"emotion":"idle","action":"none","text":"实际回答"}。'
    "emotion 只能使用 idle、happy、curious、sad、sleepy；"
    "action 只能使用 none、bounce、nod、shake、wave。thinking 由程序控制，"
    "不要输出 thinking。情绪和动作要符合语境，不要每次都使用夸张动作；"
    "大多数普通回答允许 emotion 为 idle、action 为 none。"
    "text 中可以在确有必要时使用 Markdown，但普通聊天仍应自然口语化。"
)


class AIClientError(RuntimeError):
    """An error safe to present directly in the chat UI."""


class AIClient:
    """Stateful DeepSeek client using the OpenAI-compatible HTTP endpoint."""

    def __init__(self, settings: AppConfig = config) -> None:
        self.settings = settings
        self.messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def send_message(self, message: str) -> AIResponse:
        """Send one user message and return the assistant text.

        This method is synchronous by design. The UI runs it in a QThread.
        """
        clean_message = message.strip()
        if not clean_message:
            raise AIClientError("消息不能为空。")
        if not self.settings.deepseek_api_key:
            raise AIClientError(
                "还没有配置 DeepSeek API Key。请复制 .env.example 为 .env，"
                "然后填写 DEEPSEEK_API_KEY。"
            )

        pending_messages = [
            *self.messages,
            {"role": "user", "content": clean_message},
        ]
        try:
            response = requests.post(
                f"{self.settings.deepseek_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.deepseek_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.settings.deepseek_model,
                    "messages": pending_messages,
                    "stream": False,
                },
                timeout=self.settings.request_timeout_seconds,
            )
        except requests.Timeout as exc:
            logger.warning("DeepSeek request timed out")
            raise AIClientError("DeepSeek 响应超时，请稍后再试。") from exc
        except requests.RequestException as exc:
            logger.warning("DeepSeek network request failed: %s", type(exc).__name__)
            raise AIClientError("暂时无法连接 DeepSeek，请检查网络后重试。") from exc

        if response.status_code == 401:
            logger.warning("DeepSeek rejected credentials (HTTP 401)")
            raise AIClientError("DeepSeek API Key 无效，请检查 .env 配置。")
        if response.status_code == 429:
            logger.warning("DeepSeek rate limit or quota error (HTTP 429)")
            raise AIClientError("DeepSeek 请求过于频繁或额度不足，请稍后再试。")
        if not response.ok:
            logger.warning("DeepSeek service error HTTP %s", response.status_code)
            raise AIClientError(f"DeepSeek 服务返回错误（HTTP {response.status_code}）。")

        try:
            payload: dict[str, Any] = response.json()
            reply = payload["choices"][0]["message"]["content"].strip()
        except (ValueError, KeyError, IndexError, AttributeError) as exc:
            logger.warning("DeepSeek response schema was not recognized")
            raise AIClientError("DeepSeek 返回了无法识别的数据。") from exc
        if not reply:
            raise AIClientError("DeepSeek 没有返回回复，请重试。")

        self.messages.extend(
            (
                {"role": "user", "content": clean_message},
                {"role": "assistant", "content": reply},
            )
        )
        return parse_ai_response(reply)
