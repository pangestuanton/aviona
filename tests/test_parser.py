from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base, ChatMessage, Memory, TimedReminder
from app.ai.parser import generate_chat_response
from app.config import Settings

# Create in-memory database engine for unit tests
test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def mock_settings():
    return Settings(
        telegram_bot_token="test_token",
        openrouter_api_key="test_api_key",
        ai_base_url="https://api.openai.com/v1",
        ai_model="gpt-4",
        timezone="Asia/Jakarta",
        database_url="sqlite:///:memory:",
        reminder_check_interval_seconds=60,
    )


@patch("app.ai.parser.SessionLocal", TestSessionLocal)
@patch("app.ai.parser.get_settings")
@patch("app.ai.parser.OpenAI")
def test_generate_chat_response_no_key(mock_openai_class, mock_get_settings):
    # Set settings with no API key
    mock_get_settings.return_value = Settings(
        telegram_bot_token="test_token",
        openrouter_api_key=None,
        ai_base_url=None,
        ai_model="gpt-4",
        timezone="Asia/Jakarta",
        database_url="sqlite:///:memory:",
        reminder_check_interval_seconds=60,
    )
    
    response = generate_chat_response(user_id=123, message_text="Halo")
    assert "API Key" in response
    
    # Check messages saved to history
    with TestSessionLocal() as db:
        msgs = db.query(ChatMessage).filter(ChatMessage.user_id == 123).all()
        assert len(msgs) == 2
        assert msgs[0].role == "user"
        assert msgs[0].content == "Halo"
        assert msgs[1].role == "assistant"
        assert "API Key" in msgs[1].content


@patch("app.ai.parser.SessionLocal", TestSessionLocal)
@patch("app.ai.parser.get_settings")
@patch("app.ai.parser.OpenAI")
def test_generate_chat_response_success(mock_openai_class, mock_get_settings, mock_settings):
    mock_get_settings.return_value = mock_settings
    
    # Mock OpenAI client
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="Halo Anton! Aku siap bantu. [MEMORY: User bernama Anton]"))
    ]
    mock_client.chat.completions.create.return_value = mock_completion
    
    response = generate_chat_response(user_id=12345, message_text="Nama saya Anton")
    
    # Check response text strips the memory tag
    assert response == "Halo Anton! Aku siap bantu."
    
    # Check database status
    with TestSessionLocal() as db:
        # Check messages in history
        msgs = db.query(ChatMessage).filter(ChatMessage.user_id == 12345).all()
        assert len(msgs) == 2
        assert msgs[0].content == "Nama saya Anton"
        assert msgs[1].content == "Halo Anton! Aku siap bantu."
        
        # Check long-term memory save
        mems = db.query(Memory).filter(Memory.user_id == 12345).all()
        assert len(mems) == 1
        assert mems[0].content == "User bernama Anton"


@patch("app.ai.parser.SessionLocal", TestSessionLocal)
@patch("app.ai.parser.get_settings")
@patch("app.ai.parser.OpenAI")
def test_generate_chat_response_with_reminder(mock_openai_class, mock_get_settings, mock_settings):
    mock_get_settings.return_value = mock_settings
    
    # Mock OpenAI client
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="Oke Anton, nanti aku ingetin jam 16.00 ya! [REMINDER: 2026-06-16 16:00:00 | Rapat 30 menit lagi!] [MEMORY: User memiliki rapat hari ini]"))
    ]
    mock_client.chat.completions.create.return_value = mock_completion
    
    response = generate_chat_response(user_id=12345, message_text="Ingetin aku jam 16:30 ada rapat")
    
    # Check response text strips the reminder and memory tags
    assert response == "Oke Anton, nanti aku ingetin jam 16.00 ya!"
    
    # Check database status
    with TestSessionLocal() as db:
        # Check long-term memory save
        mems = db.query(Memory).filter(Memory.user_id == 12345).all()
        assert len(mems) == 1
        assert mems[0].content == "User memiliki rapat hari ini"
        
        # Check timed reminders save
        reminders = db.query(TimedReminder).filter(TimedReminder.user_id == 12345).all()
        assert len(reminders) == 1
        assert reminders[0].message == "Rapat 30 menit lagi!"
        # In mock settings, the timezone is "Asia/Jakarta" (UTC+7)
        # 2026-06-16 16:00:00 Asia/Jakarta in UTC is 2026-06-16 09:00:00
        assert reminders[0].remind_at.strftime("%Y-%m-%d %H:%M:%S") == "2026-06-16 09:00:00"
