from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import Memory, UserProfile


def save_memory(db: Session, user_id: int, content: str, category: str = "general", importance: int = 1) -> Memory:
    memory = Memory(
        user_id=user_id,
        content=content,
        category=category,
        importance=importance,
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def set_user_preference(db: Session, user_id: int, preference: str) -> UserProfile:
    profile = db.get(UserProfile, user_id)
    if profile is None:
        profile = UserProfile(user_id=user_id, reminder_preference=preference)
        db.add(profile)
    else:
        profile.reminder_preference = preference

    save_memory(db, user_id, preference, category="preference", importance=3)
    db.commit()
    db.refresh(profile)
    return profile


def list_memories(db: Session, user_id: int, limit: int = 10) -> list[Memory]:
    return (
        db.query(Memory)
        .filter(Memory.user_id == user_id)
        .order_by(Memory.importance.desc(), Memory.created_at.desc())
        .limit(limit)
        .all()
    )
