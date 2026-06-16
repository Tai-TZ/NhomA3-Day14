import os
from typing import Optional

from openai import AsyncOpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_api_key() -> Optional[str]:
    return os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")


def is_live_mode() -> bool:
    return bool(get_api_key())


def get_async_client() -> Optional[AsyncOpenAI]:
    api_key = get_api_key()
    if not api_key:
        return None
    return AsyncOpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", OPENROUTER_BASE_URL),
    )
