from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session

from app.database.models import UserProfile, ChatMessage, Memory, TimedReminder
from app.utils.datetime_utils import utc_now


def get_user_profile(db: Session, user_id: int) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        try:
            db.add(profile)
            db.commit()
            db.refresh(profile)
        except Exception:
            db.rollback()
            raise
    return profile


def save_chat_message(db: Session, user_id: int, role: str, content: str) -> ChatMessage:
    msg = ChatMessage(
        user_id=user_id,
        role=role,
        content=content,
    )
    try:
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg
    except Exception:
        db.rollback()
        raise


def get_chat_history(db: Session, user_id: int, limit: int = 10) -> list[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )[::-1]  # Return in chronological order


def clear_chat_history(db: Session, user_id: int) -> None:
    try:
        db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
        db.commit()
    except Exception:
        db.rollback()
        raise


def clear_user_memories(db: Session, user_id: int) -> None:
    try:
        db.query(Memory).filter(Memory.user_id == user_id).delete()
        db.commit()
    except Exception:
        db.rollback()
        raise


def save_memory(db: Session, user_id: int, content: str, category: str = "general", importance: int = 1) -> Memory:
    memory = Memory(
        user_id=user_id,
        content=content,
        category=category,
        importance=importance,
    )
    try:
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory
    except Exception:
        db.rollback()
        raise


def list_memories(db: Session, user_id: int, limit: int = 10) -> list[Memory]:
    return (
        db.query(Memory)
        .filter(Memory.user_id == user_id)
        .order_by(Memory.importance.desc(), Memory.created_at.desc())
        .limit(limit)
        .all()
    )


def get_memory_by_id(db: Session, memory_id: int) -> Memory | None:
    return db.query(Memory).filter(Memory.id == memory_id).first()


def delete_memory_by_id(db: Session, memory_id: int) -> None:
    try:
        db.query(Memory).filter(Memory.id == memory_id).delete()
        db.commit()
    except Exception:
        db.rollback()
        raise


def save_timed_reminder(db: Session, user_id: int, remind_at_utc: datetime, message: str) -> TimedReminder:
    reminder = TimedReminder(
        user_id=user_id,
        remind_at=remind_at_utc,
        message=message,
        sent_count=0,
    )
    try:
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        return reminder
    except Exception:
        db.rollback()
        raise


def get_due_timed_reminders(db: Session, now_utc: datetime) -> list[TimedReminder]:
    from sqlalchemy import or_
    from datetime import timedelta
    
    one_minute_ago = now_utc - timedelta(minutes=1)
    return (
        db.query(TimedReminder)
        .filter(
            TimedReminder.remind_at <= now_utc,
            TimedReminder.sent_count < 3,
            or_(
                TimedReminder.last_sent_at == None,
                TimedReminder.last_sent_at <= one_minute_ago
            )
        )
        .all()
    )
