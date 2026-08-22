"""Environment-backed configuration for MechaPet."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True, slots=True)
class AppConfig:
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
    deepseek_base_url: str = os.getenv(
        "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
    ).rstrip("/")
    deepseek_model: str = os.getenv(
        "DEEPSEEK_MODEL", "deepseek-v4-flash"
    ).strip()
    request_timeout_seconds: int = 60


config = AppConfig()


# V0.2 interaction tuning. Keep these centralized so animation feel can be
# adjusted without touching controllers or widgets.
IDLE_ANIMATION_DURATION = 3200
CLICK_ANIMATION_DURATION = 800
IDLE_BEHAVIOR_MIN_SECONDS = 30
IDLE_BEHAVIOR_MAX_SECONDS = 90
SPEECH_BUBBLE_BASE_DURATION = 5000
SPEECH_BUBBLE_MAX_LENGTH = 120
PET_ANIMATION_OFFSET = 7
