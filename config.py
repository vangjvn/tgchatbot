import os
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    IS_USE_PROXY: bool = os.getenv("IS_USE_PROXY", "yes").lower() == "yes"
    LOCAL_PROXY_TYPE: str = os.getenv("LOCAL_PROXY_TYPE", "socks5")
    LOCAL_PROXY_PORT: int = int(os.getenv("LOCAL_PROXY_PORT", 8080))

    PROXY_URL: Optional[str] = f"{LOCAL_PROXY_TYPE}://127.0.0.1:{LOCAL_PROXY_PORT}"


    TG_BOT_TOKEN: str = os.getenv("TG_BOT_TOKEN", "")
    AI_CHAT_URL: str = os.getenv("AI_CHAT_URL", "")


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
