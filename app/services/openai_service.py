import json
from typing import Any

from openai import AsyncOpenAI

from app.config import Settings


ENTRY_SCHEMA = {
    "type": "object",
    "properties": {
        "improved_text": {"type": "string"},
        "summary": {"type": "string"},
        "technical_progress": {"type": "array", "items": {"type": "string"}},
        "tools": {"type": "array", "items": {"type": "string"}},
        "learnings": {"type": "array", "items": {"type": "string"}},
        "difficulties": {"type": "array", "items": {"type": "string"}},
        "pending_items": {"type": "array", "items": {"type": "string"}},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "improved_text",
        "summary",
        "technical_progress",
        "tools",
        "learnings",
        "difficulties",
        "pending_items",
        "tags",
    ],
    "additionalProperties": False,
}


class OpenAIService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def transcribe_audio(self, filename: str, content: bytes) -> str:
        response = await self.client.audio.transcriptions.create(
            model=self.settings.openai_transcription_model,
            file=(filename, content),
            response_format="text",
            prompt=(
                "El audio es una bitacora profesional en espanol de un ingeniero de "
                "sistemas y analista de datos. Respeta nombres de herramientas como "
                "Python, SQL, Power BI, pandas, Railway, FastAPI, MongoDB y PostgreSQL."
            ),
        )
        return str(response)

    async def draft_entry(self, text: str) -> dict[str, Any]:
        response = await self.client.responses.create(
            model=self.settings.openai_text_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Eres un editor y mentor profesional. Convierte una entrada diaria "
                        "informal en una bitacora clara, fiel y accionable. No inventes "
                        "hechos. Si algo no aparece, dejalo como lista vacia."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Entrada original:\n{text}",
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "daily_log_entry",
                    "schema": ENTRY_SCHEMA,
                    "strict": True,
                }
            },
        )
        return json.loads(response.output_text)

    async def revise_entry(self, current_text: str, instruction: str) -> dict[str, Any]:
        response = await self.client.responses.create(
            model=self.settings.openai_text_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Actualiza una bitacora diaria siguiendo la instruccion del usuario. "
                        "Mantente fiel a lo indicado y conserva el mismo formato estructurado."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Bitacora actual:\n{current_text}\n\n"
                        f"Instruccion de cambio:\n{instruction}"
                    ),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "daily_log_entry_revision",
                    "schema": ENTRY_SCHEMA,
                    "strict": True,
                }
            },
        )
        return json.loads(response.output_text)

    async def weekly_report(self, iso_week: str, approved_entries: list[str]) -> str:
        joined_entries = "\n\n---\n\n".join(approved_entries)
        response = await self.client.responses.create(
            model=self.settings.openai_text_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Eres un mentor tecnico. Genera un reporte semanal breve, honesto "
                        "y util para el crecimiento profesional de un ingeniero de sistemas "
                        "con enfoque en analisis de datos. No inventes informacion."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Semana: {iso_week}\n\n"
                        "Entradas aprobadas:\n"
                        f"{joined_entries}\n\n"
                        "Usa exactamente estas secciones:\n"
                        "Resumen semanal\n"
                        "Avances tecnicos\n"
                        "Herramientas practicadas\n"
                        "Aprendizajes clave\n"
                        "Dificultades repetidas\n"
                        "Puntos a mejorar\n"
                        "Consejos para la proxima semana\n"
                        "Plan sugerido"
                    ),
                },
            ],
        )
        return response.output_text
