# Bitacora AI

Bot de Telegram para registrar una bitacora profesional diaria con texto o voz, mejorar la redaccion con IA, pedir aprobacion antes de guardar y generar un reporte semanal automatico.

## Flujo

1. Envias texto o nota de voz por Telegram.
2. Si es voz, el backend descarga el audio y lo transcribe con OpenAI.
3. El modelo mejora la redaccion y extrae campos utiles.
4. El bot devuelve un borrador con botones: Aprobar, Editar o Descartar.
5. Al aprobar, la entrada queda asociada a la semana correspondiente.
6. El domingo, un job genera y envia:
   - Resumen semanal
   - Avances tecnicos
   - Herramientas practicadas
   - Aprendizajes clave
   - Dificultades repetidas
   - Puntos a mejorar
   - Consejos para la proxima semana
   - Plan sugerido

## Stack

- FastAPI
- PostgreSQL
- Telegram Bot API
- OpenAI audio transcription y texto
- Railway para despliegue

## Variables de entorno

Copia `.env.example` a `.env` en local o configura las mismas variables en Railway.

Variables principales:

- `APP_BASE_URL`: URL publica de Railway.
- `DATABASE_URL`: URL de PostgreSQL.
- `TELEGRAM_BOT_TOKEN`: token de BotFather.
- `TELEGRAM_WEBHOOK_SECRET`: secreto para proteger el webhook.
- `TELEGRAM_ALLOWED_USER_IDS`: IDs de Telegram permitidos, separados por coma.
- `OPENAI_API_KEY`: clave de OpenAI.
- `OPENAI_TRANSCRIPTION_MODEL`: usa `whisper-1` si quieres Whisper clasico, o `gpt-4o-transcribe` para transcripcion mas nueva.
- `OPENAI_TEXT_MODEL`: modelo GPT usado para redactar, estructurar y resumir.
- `WEEKLY_REPORT_CRON_TOKEN`: secreto para ejecutar el reporte semanal.

## Desarrollo local

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload
```

## Configurar webhook de Telegram

Cuando Railway te de una URL publica:

```text
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<APP_BASE_URL>/webhooks/telegram/<TELEGRAM_WEBHOOK_SECRET>
```

Tambien puedes abrir:

```text
<APP_BASE_URL>/telegram/set-webhook
```

## Railway

Lee [docs/railway-env.md](docs/railway-env.md) para configurar las variables del servicio `bitacora-ai`.

## Cron semanal en Railway

Crea un servicio cron que ejecute los domingos en la manana de Colombia. Railway usa UTC; para 8:00 a. m. Colombia:

```text
0 13 * * 0
```

Comando recomendado:

```bash
python -m app.jobs.weekly_report
```

## Endpoints utiles

- `GET /health`
- `GET /telegram/set-webhook`
- `POST /webhooks/telegram/{secret}`
- `POST /jobs/weekly-report?token=<WEEKLY_REPORT_CRON_TOKEN>`
