from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.database.models import Task, Reminder, CourseSchedule


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def create_task_from_parsed(db: Session, user_id: int, parsed: dict[str, Any], raw_text: str) -> Task:
    title = parsed.get("title") or parsed.get("description") or raw_text
    deadline = _parse_dt(parsed.get("deadline") or parsed.get("event_time"))

    task = Task(
        user_id=user_id,
        title=title,
        course=parsed.get("course"),
        description=parsed.get("description"),
        deadline=deadline,
        priority=parsed.get("priority") or "normal",
        raw_text=raw_text,
    )
    db.add(task)
    db.flush()

    _create_reminders_for_task(db, task, parsed.get("reminders") or [])

    db.commit()
    db.refresh(task)
    return task


def update_task_from_parsed(db: Session, user_id: int, parsed: dict[str, Any], raw_text: str) -> Task | None:
    target = parsed.get("target") or raw_text
    task = _find_task_by_keyword(db, user_id, target)
    if not task:
        return None

    if parsed.get("title"):
        task.title = parsed["title"]
    if parsed.get("course"):
        task.course = parsed["course"]
    if parsed.get("description"):
        task.description = parsed["description"]
    
    new_deadline = _parse_dt(parsed.get("deadline") or parsed.get("event_time") or parsed.get("new_value"))
    if new_deadline:
        task.deadline = new_deadline
        # Recreate reminders if deadline changed
        for r in task.reminders:
            r.is_active = False
        _create_reminders_for_task(db, task, parsed.get("reminders") or [])
    
    if parsed.get("priority"):
        task.priority = parsed["priority"]

    db.commit()
    db.refresh(task)
    return task


def _create_reminders_for_task(db: Session, task: Task, reminder_strs: list[str]) -> None:
    for remind_str in reminder_strs:
        remind_at = _parse_dt(remind_str)
        if not remind_at:
            continue

        reminder = Reminder(
            task_id=task.id,
            user_id=task.user_id,
            remind_at=remind_at,
            message=f"Pengingat: {task.title}",
        )
        db.add(reminder)


def _find_task_by_keyword(db: Session, user_id: int, keyword: str) -> Task | None:
    # Clean keyword
    clean_keyword = (
        keyword.lower()
        .replace("ubah", "")
        .replace("ganti", "")
        .replace("hapus", "")
        .replace("selesai", "")
        .replace("tugas", "")
        .replace("deadline", "")
        .strip()
    )
    if not clean_keyword:
        return None

    tasks = (
        db.query(Task)
        .filter(Task.user_id == user_id, Task.status != "deleted")
        .order_by(Task.created_at.desc())
        .all()
    )

    # Try exact match first
    for task in tasks:
        if clean_keyword == task.title.lower() or clean_keyword == (task.course or "").lower():
            return task

    # Try partial match
    for task in tasks:
        if clean_keyword in task.title.lower() or clean_keyword in (task.course or "").lower():
            return task

    return None


def delete_task_by_text(db: Session, user_id: int, target: str) -> int:
    task = _find_task_by_keyword(db, user_id, target)
    if not task:
        return 0

    task.status = "deleted"
    task.deleted_at = datetime.utcnow()
    for r in task.reminders:
        r.is_active = False

    db.commit()
    return 1


def mark_task_done_by_text(db: Session, user_id: int, target: str) -> Task | None:
    task = _find_task_by_keyword(db, user_id, target)
    if not task:
        # If no specific keyword, maybe they mean the latest pending task?
        task = (
            db.query(Task)
            .filter(Task.user_id == user_id, Task.status == "pending")
            .order_by(Task.deadline.asc())
            .first()
        )

    if task:
        task.status = "done"
        task.completed_at = datetime.utcnow()
        for r in task.reminders:
            r.is_active = False
        db.commit()
        db.refresh(task)
        return task

    return None


def create_schedule_from_parsed(db: Session, user_id: int, parsed: dict[str, Any], raw_text: str) -> CourseSchedule:
    schedule = CourseSchedule(
        user_id=user_id,
        course=parsed.get("course") or parsed.get("title") or raw_text,
        day_of_week=parsed.get("day_of_week"),
        start_time=parsed.get("start_time"),
        end_time=parsed.get("end_time"),
        room=parsed.get("room"),
        lecturer=parsed.get("lecturer"),
        raw_text=raw_text,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def get_tasks_between(db: Session, user_id: int, start: datetime, end: datetime) -> list[Task]:
    return (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.deadline.is_not(None),
            Task.deadline >= start,
            Task.deadline < end,
            Task.status != "deleted",
        )
        .order_by(Task.deadline.asc())
        .all()
    )


def get_due_reminders(db: Session, now: datetime) -> list[Reminder]:
    return (
        db.query(Reminder)
        .filter(
            Reminder.sent == False,
            Reminder.is_active == True,
            Reminder.remind_at <= now
        )
        .order_by(Reminder.remind_at.asc())
        .limit(50)
        .all()
    )


def get_user_profile(db: Session, user_id: int) -> UserProfile:
    from app.database.models import UserProfile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile
