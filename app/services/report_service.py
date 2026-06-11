from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyEntry, EntryStatus, User, WeeklyReport, utcnow
from app.services.openai_service import OpenAIService
from app.services.telegram_service import TelegramService


async def generate_weekly_reports(
    session: AsyncSession,
    openai_service: OpenAIService,
    telegram_service: TelegramService,
    iso_week: str,
) -> int:
    users_result = await session.execute(select(User))
    users = users_result.scalars().all()
    delivered = 0

    for user in users:
        entries_result = await session.execute(
            select(DailyEntry)
            .where(DailyEntry.user_id == user.id)
            .where(DailyEntry.iso_week == iso_week)
            .where(DailyEntry.status == EntryStatus.APPROVED)
            .order_by(DailyEntry.entry_date.asc())
        )
        entries = entries_result.scalars().all()
        if not entries:
            continue

        entry_texts = [entry.improved_text or entry.raw_text for entry in entries]
        report_text = await openai_service.weekly_report(iso_week, entry_texts)

        stmt = (
            insert(WeeklyReport)
            .values(
                user_id=user.id,
                iso_week=iso_week,
                report_text=report_text,
                structured_data={},
                delivered_at=utcnow(),
            )
            .on_conflict_do_update(
                constraint="uq_weekly_report_user_week",
                set_={"report_text": report_text, "delivered_at": utcnow()},
            )
        )
        await session.execute(stmt)
        await telegram_service.send_message(user.telegram_chat_id, report_text)
        delivered += 1

    await session.commit()
    return delivered
