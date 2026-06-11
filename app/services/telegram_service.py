from typing import Any

import httpx

from app.config import Settings


class TelegramService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    async def request(self, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{self.base_url}/{method}", json=payload or {})
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                raise RuntimeError(data)
            return data

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        await self.request(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text[:4096],
                "reply_markup": reply_markup,
            },
        )

    async def answer_callback_query(self, callback_query_id: str, text: str) -> None:
        await self.request("answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text})

    async def set_webhook(self) -> dict[str, Any]:
        webhook_url = (
            f"{self.settings.app_base_url.rstrip('/')}"
            f"/webhooks/telegram/{self.settings.telegram_webhook_secret}"
        )
        return await self.request("setWebhook", {"url": webhook_url})

    async def get_file_bytes(self, file_id: str) -> tuple[str, bytes]:
        file_response = await self.request("getFile", {"file_id": file_id})
        file_path = file_response["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{self.settings.telegram_bot_token}/{file_path}"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(file_url)
            response.raise_for_status()
            return file_path.split("/")[-1], response.content


def review_keyboard(entry_id: int) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "Aprobar", "callback_data": f"approve:{entry_id}"},
                {"text": "Editar", "callback_data": f"edit:{entry_id}"},
                {"text": "Descartar", "callback_data": f"reject:{entry_id}"},
            ]
        ]
    }
