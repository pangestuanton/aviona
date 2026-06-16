import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def clean_api_key(key: str | None) -> str | None:
    if not key:
        return None
    key = key.strip().strip('"').strip("'")
    # Auto-prepend OpenRouter prefix if the user copied only the 64-character hex hash on Railway
    if len(key) == 64 and not key.startswith("sk-"):
        key = f"sk-or-v1-{key}"
    return key


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    openrouter_api_key: str | None
    ai_base_url: str | None
    ai_model: str
    timezone: str
    database_url: str
    reminder_check_interval_seconds: int


def get_settings() -> Settings:
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip().strip('"').strip("'"),
        openrouter_api_key=clean_api_key(os.getenv("OPENROUTER_API_KEY")),
        ai_base_url=os.getenv("AI_BASE_URL") or None,
        ai_model=os.getenv("AI_MODEL", "google/gemini-2.5-flash"),
        timezone=os.getenv("APP_TIMEZONE", "Asia/Jakarta"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///study_bot.db"),
        reminder_check_interval_seconds=int(os.getenv("REMINDER_CHECK_INTERVAL_SECONDS", "60")),
    )
