# Railway environment variables

Configura estas variables en el servicio `bitacora-ai`, no en el servicio `Postgres`.

## Requeridas

```text
APP_ENV=production
APP_BASE_URL=https://TU-DOMINIO.up.railway.app
DATABASE_URL=${{Postgres.DATABASE_URL}}
TELEGRAM_BOT_TOKEN=token_de_botfather
TELEGRAM_WEBHOOK_SECRET=un_secreto_largo_aleatorio
TELEGRAM_ALLOWED_USER_IDS=tu_id_de_telegram
OPENAI_API_KEY=sk-...
OPENAI_TRANSCRIPTION_MODEL=whisper-1
OPENAI_TEXT_MODEL=gpt-5.5
WEEKLY_REPORT_CRON_TOKEN=otro_secreto_largo_aleatorio
REPORT_TIMEZONE=America/Bogota
REPORT_LOOKBACK_DAYS=7
```

## Notas

- Usa `DATABASE_URL`, no `DATABASE_PUBLIC_URL`, porque la app y Postgres viven dentro de Railway.
- No pegues `POSTGRES_PASSWORD` manualmente en el repo.
- Si rotas el servicio de Postgres, Railway actualiza las variables referenciadas.
- Despues del primer deploy exitoso, abre:

```text
https://TU-DOMINIO.up.railway.app/telegram/set-webhook
```

Eso registra el webhook de Telegram.

## Cron semanal

Crea otro servicio o job cron con:

```bash
python -m app.jobs.weekly_report
```

Para domingo 8:00 a. m. Colombia:

```text
0 13 * * 0
```
