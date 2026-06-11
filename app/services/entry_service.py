from datetime import timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyEntry, EntryRevision, EntryStatus, User, utcnow
from app.services.openai_service import OpenAIService
from app.utils import iso_week_key, now_in_timezone


def format_draft(structured: dict[str, Any]) -> str:
    def bullets(values: list[str]) -> str:
        return "\n".join(f"- {item}" for item in values) if values else "- Sin datos"

    return (
        f"{structured['improved_text']}\n\n"
        "Herramientas usadas:\n"
        f"{bullets(structured['tools'])}\n\n"
        "Aprendizajes:\n"
        f"{bullets(structured['learnings'])}\n\n"
        "Dificultades:\n"
        f"{bullets(structured['difficulties'])}\n\n"
        "Pendientes:\n"
        f"{bullets(structured['pending_items'])}"
    )


async def get_or_create_user(
    session: AsyncSession,
    telegram_user_id: int,
    telegram_chat_id: int,
    first_name: str | None,
    username: str | None,
) -> User:
    result = await session.execute(select(User).where(User.telegram_user_id == telegram_user_id))
    user = result.scalar_one_or_none()
    if user:
        user.telegram_chat_id = telegram_chat_id
        user.first_name = first_name
        user.username = username
        user.updated_at = utcnow()
        return user

    user = User(
        telegram_user_id=telegram_user_id,
        telegram_chat_id=telegram_chat_id,
        first_name=first_name,
        username=username,
    )
    session.add(user)
    await session.flush()
    return user


async def find_pending_entry(session: AsyncSession, user_id: int) -> DailyEntry | None:
    result = await session.execute(
        select(DailyEntry)
        .where(DailyEntry.user_id == user_id)
        .where(DailyEntry.status == EntryStatus.PENDING_REVIEW)
        .order_by(DailyEntry.created_at.desc())
    )
    return result.scalars().first()


async def create_draft_entry(
    session: AsyncSession,
    openai_service: OpenAIService,
    user: User,
    source: str,
    raw_text: str,
    telegram_message_id: int | None,
) -> DailyEntry:
    local_now = now_in_timezone("America/Bogota")
    structured = await openai_service.draft_entry(raw_text)
    improved_text = format_draft(structured)
    entry = DailyEntry(
        user_id=user.id,
        telegram_message_id=telegram_message_id,
        source=source,
        raw_text=raw_text,
        transcription=raw_text if source == "voice" else None,
        improved_text=improved_text,
        structured_data=structured,
        status=EntryStatus.PENDING_REVIEW,
        entry_date=local_now.astimezone(timezone.utc),
        iso_week=iso_week_key(local_now),
    )
    session.add(entry)
    await session.flush()
    session.add(EntryRevision(entry_id=entry.id, text=improved_text, structured_data=structured))
    return entry


async def revise_pending_entry(
    session: AsyncSession,
    openai_service: OpenAIService,
    entry: DailyEntry,
    instruction: str,
) -> DailyEntry:
    structured = await openai_service.revise_entry(entry.improved_text or "", instruction)
    improved_text = format_draft(structured)
    entry.improved_text = improved_text
    entry.structured_data = structured
    entry.updated_at = utcnow()
    session.add(
        EntryRevision(
            entry_id=entry.id,
            instruction=instruction,
            text=improved_text,
            structured_data=structured,
        )
    )
    return entry


async def approve_entry(session: AsyncSession, entry_id: int) -> DailyEntry | None:
    entry = await session.get(DailyEntry, entry_id)
    if not entry:
        return None
    entry.status = EntryStatus.APPROVED
    entry.updated_at = utcnow()
    return entry


async def reject_entry(session: AsyncSession, entry_id: int) -> DailyEntry | None:
    entry = await session.get(DailyEntry, entry_id)
    if not entry:
        return None
    entry.status = EntryStatus.REJECTED
    entry.updated_at = utcnow()
    return entry
