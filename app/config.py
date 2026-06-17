import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

DEFAULT_AI_MODELS = (
    "openai/gpt-oss-20b:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-nano-9b-v2:free",
)


def clean_api_key(key: str | None) -> str | None:
    if not key:
        return None
    key = key.strip().strip('"').strip("'")
    # Auto-prepend OpenRouter prefix if the user copied only the 64-character hex hash on Railway
    if len(key) == 64 and not key.startswith("sk-"):
        key = f"sk-or-v1-{key}"
    return key


def parse_ai_models(models: str | None, legacy_model: str | None) -> tuple[str, ...]:
    if models:
        parsed_models = tuple(
            model.strip()
            for model in models.replace("\n", ",").split(",")
            if model.strip()
        )
        if parsed_models:
            return tuple(dict.fromkeys(parsed_models))

    legacy_model = (legacy_model or "").strip()
    if legacy_model and legacy_model != "openrouter/free":
        return (legacy_model,)

    return DEFAULT_AI_MODELS


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    openrouter_api_key: str | None
    ai_base_url: str | None
    ai_model: str
    timezone: str
    database_url: str
    reminder_check_interval_seconds: int
    ai_models: tuple[str, ...] = DEFAULT_AI_MODELS


def get_settings() -> Settings:
    ai_models = parse_ai_models(os.getenv("AI_MODELS"), os.getenv("AI_MODEL"))
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip().strip('"').strip("'"),
        openrouter_api_key=clean_api_key(os.getenv("OPENROUTER_API_KEY")),
        ai_base_url=os.getenv("AI_BASE_URL") or "https://openrouter.ai/api/v1",
        ai_model=ai_models[0],
        ai_models=ai_models,
        timezone=os.getenv("APP_TIMEZONE", "Asia/Jakarta"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///study_bot.db"),
        reminder_check_interval_seconds=int(os.getenv("REMINDER_CHECK_INTERVAL_SECONDS", "60")),
    )
