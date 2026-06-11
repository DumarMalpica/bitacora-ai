from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session, init_db
from app.models import DailyEntry
from app.services.entry_service import (
    approve_entry,
    create_draft_entry,
    find_pending_entry,
    get_or_create_user,
    reject_entry,
    revise_pending_entry,
)
from app.services.openai_service import OpenAIService
from app.services.report_service import generate_weekly_reports
from app.services.telegram_service import TelegramService, review_keyboard
from app.utils import now_in_timezone, previous_iso_week_key

app = FastAPI(title="Bitacora AI", version="0.1.0")


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/telegram/set-webhook")
async def set_telegram_webhook(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    telegram = TelegramService(settings)
    return await telegram.set_webhook()


@app.post("/webhooks/telegram/{secret}")
async def telegram_webhook(
    secret: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, bool]:
    if secret != settings.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    update = await request.json()
    telegram = TelegramService(settings)
    openai_service = OpenAIService(settings)

    if "callback_query" in update:
        await handle_callback_query(update["callback_query"], session, telegram)
        await session.commit()
        return {"ok": True}

    message = update.get("message")
    if message:
        await handle_message(message, session, telegram, openai_service, settings)
        await session.commit()

    return {"ok": True}


async def handle_message(
    message: dict[str, Any],
    session: AsyncSession,
    telegram: TelegramService,
    openai_service: OpenAIService,
    settings: Settings,
) -> None:
    from_user = message.get("from") or {}
    telegram_user_id = int(from_user["id"])
    if message.get("text") == "/id":
        await telegram.send_message(
            int(message["chat"]["id"]),
            f"Tu Telegram user id es: {telegram_user_id}\nChat id: {message['chat']['id']}",
        )
        return

    if settings.allowed_user_ids and telegram_user_id not in settings.allowed_user_ids:
        await telegram.send_message(
            int(message["chat"]["id"]),
            (
                "Este bot aun es privado.\n\n"
                f"Tu Telegram user id detectado es: {telegram_user_id}"
            ),
        )
        return

    user = await get_or_create_user(
        session=session,
        telegram_user_id=telegram_user_id,
        telegram_chat_id=int(message["chat"]["id"]),
        first_name=from_user.get("first_name"),
        username=from_user.get("username"),
    )

    if text := message.get("text"):
        pending = await find_pending_entry(session, user.id)
        if pending and not text.startswith("/"):
            entry = await revise_pending_entry(session, openai_service, pending, text)
            await telegram.send_message(
                user.telegram_chat_id,
                "Actualice tu borrador:\n\n" + (entry.improved_text or ""),
                reply_markup=review_keyboard(entry.id),
            )
            return

        entry = await create_draft_entry(
            session=session,
            openai_service=openai_service,
            user=user,
            source="text",
            raw_text=text,
            telegram_message_id=message.get("message_id"),
        )
        await telegram.send_message(
            user.telegram_chat_id,
            "Prepare esta entrada para tu bitacora:\n\n" + (entry.improved_text or ""),
            reply_markup=review_keyboard(entry.id),
        )
        return

    if voice := message.get("voice"):
        await telegram.send_message(user.telegram_chat_id, "Recibi tu audio. Lo transcribo y preparo.")
        filename, content = await telegram.get_file_bytes(voice["file_id"])
        transcript = await openai_service.transcribe_audio(filename, content)
        entry = await create_draft_entry(
            session=session,
            openai_service=openai_service,
            user=user,
            source="voice",
            raw_text=transcript,
            telegram_message_id=message.get("message_id"),
        )
        await telegram.send_message(
            user.telegram_chat_id,
            "Transcripcion y borrador listos:\n\n" + (entry.improved_text or ""),
            reply_markup=review_keyboard(entry.id),
        )
        return

    await telegram.send_message(user.telegram_chat_id, "Por ahora recibo texto o notas de voz.")


async def handle_callback_query(
    callback_query: dict[str, Any],
    session: AsyncSession,
    telegram: TelegramService,
) -> None:
    callback_id = callback_query["id"]
    data = callback_query.get("data", "")
    message = callback_query.get("message") or {}
    chat_id = int(message.get("chat", {}).get("id"))

    action, raw_entry_id = data.split(":", 1)
    entry_id = int(raw_entry_id)

    if action == "approve":
        entry = await approve_entry(session, entry_id)
        if not entry:
            await telegram.answer_callback_query(callback_id, "No encontre esa entrada.")
            return
        await telegram.answer_callback_query(callback_id, "Entrada aprobada.")
        await telegram.send_message(chat_id, f"Guardada en la semana {entry.iso_week}.")
        return

    if action == "reject":
        entry = await reject_entry(session, entry_id)
        if not entry:
            await telegram.answer_callback_query(callback_id, "No encontre esa entrada.")
            return
        await telegram.answer_callback_query(callback_id, "Entrada descartada.")
        await telegram.send_message(chat_id, "Listo, descarte ese borrador.")
        return

    if action == "edit":
        entry = await session.get(DailyEntry, entry_id)
        if not entry:
            await telegram.answer_callback_query(callback_id, "No encontre esa entrada.")
            return
        await telegram.answer_callback_query(callback_id, "Enviame el cambio como mensaje.")
        await telegram.send_message(
            chat_id,
            "Escribeme que quieres agregar, quitar o cambiar. Ejemplo: "
            "'Agrega que tambien use pandas y elimina la parte de Power BI'.",
        )
        return


@app.post("/jobs/weekly-report")
async def weekly_report_job(
    token: str,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if token != settings.weekly_report_cron_token:
        raise HTTPException(status_code=403, detail="Invalid cron token")

    local_now = now_in_timezone(settings.report_timezone)
    iso_week = previous_iso_week_key(local_now)
    delivered = await generate_weekly_reports(
        session=session,
        openai_service=OpenAIService(settings),
        telegram_service=TelegramService(settings),
        iso_week=iso_week,
    )
    return {"iso_week": iso_week, "delivered": delivered}
