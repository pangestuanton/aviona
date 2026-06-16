import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    openai_api_key: str | None
    ai_base_url: str | None
    ai_model: str
    timezone: str
    database_url: str
    reminder_check_interval_seconds: int


def get_settings() -> Settings:
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        ai_base_url=os.getenv("AI_BASE_URL") or None,
        ai_model=os.getenv("AI_MODEL", "gpt-4.1-mini"),
        timezone=os.getenv("APP_TIMEZONE", "Asia/Jakarta"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///study_bot.db"),
        reminder_check_interval_seconds=int(os.getenv("REMINDER_CHECK_INTERVAL_SECONDS", "60")),
    )
