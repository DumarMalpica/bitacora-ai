import asyncio

from app.config import get_settings
from app.database import AsyncSessionLocal, init_db
from app.services.openai_service import OpenAIService
from app.services.report_service import generate_weekly_reports
from app.services.telegram_service import TelegramService
from app.utils import now_in_timezone, previous_iso_week_key


async def main() -> None:
    settings = get_settings()
    await init_db()
    iso_week = previous_iso_week_key(now_in_timezone(settings.report_timezone))
    async with AsyncSessionLocal() as session:
        delivered = await generate_weekly_reports(
            session=session,
            openai_service=OpenAIService(settings),
            telegram_service=TelegramService(settings),
            iso_week=iso_week,
        )
    print(f"Generated weekly reports for {iso_week}. Delivered: {delivered}")


if __name__ == "__main__":
    asyncio.run(main())
