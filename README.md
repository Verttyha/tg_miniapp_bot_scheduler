# Telegram Scheduler Mini App

Telegram Mini App and Telegram bot for collaborative schedule management, event voting, calendar sync, reminders, and attendance tracking.

The repository is structured for direct server deployment without tunnel helpers. One FastAPI service handles:

- backend API
- Telegram webhook updates
- Mini App static files
- in-process scheduler jobs

## Structure

```text
apps/
  miniapp/                  React + TypeScript + Vite source
  server/
    scheduler_app/
      api/                  HTTP routes
      bot/                  Telegram handlers
      core/                 settings, security, db, deps
      domain/               SQLAlchemy models and Pydantic schemas
      integrations/         Google and Yandex providers
      services/             business logic
      static/app/           generated Mini App bundle output
data/                       runtime SQLite data
memory-bank/                project memory and decisions
tests/                      backend test suite
```

## Stack

- Backend: FastAPI, aiogram, SQLAlchemy async
- Frontend: React, TypeScript, Vite, Telegram Mini Apps SDK
- Storage: SQLite by default, optional `DATABASE_URL` override
- Integrations: Google Calendar REST, Yandex Calendar via CalDAV

## Server Setup

### 1. Install backend dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .[dev]
```

### 2. Configure environment

```powershell
Copy-Item .env.example .env
```

Fill at least:

- `APP_SECRET`
- `BOT_TOKEN`
- `BOT_USERNAME`
- `BASE_URL=https://your-domain.example`
- `TELEGRAM_PROXY_URL=socks5://127.0.0.1:1080` (when Telegram API is blocked from your server)
- `TELEGRAM_REQUEST_TIMEOUT_SECONDS=6` (fail-fast timeout for Telegram API calls)

Recommended server defaults:

```env
APP_ENV=production
ALLOW_INSECURE_DEV_AUTH=false
SYNC_TELEGRAM_WEBHOOK_ON_STARTUP=true
TELEGRAM_PROXY_URL=
TELEGRAM_REQUEST_TIMEOUT_SECONDS=6
```

### 3. Build the Mini App

```powershell
Set-Location apps\miniapp
cmd /c npm install
cmd /c npm run build
Set-Location ..\..
```

### 4. Start the service

```powershell
.\.venv\Scripts\python -m uvicorn scheduler_app.main:app --host 0.0.0.0 --port 8000
```

Or use the package entrypoint:

```powershell
.\.venv\Scripts\telegram-scheduler
```

After startup:

- Mini App: [http://127.0.0.1:8000/app](http://127.0.0.1:8000/app)
- Healthcheck: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

## Telegram Webhook

The bot receives updates through `POST /webhooks/telegram`.

If `BASE_URL` points to a public `https` domain and `SYNC_TELEGRAM_WEBHOOK_ON_STARTUP=true`, the application syncs the webhook automatically on startup.

If your server cannot reach `api.telegram.org` directly, set `TELEGRAM_PROXY_URL` (for example, `socks5://127.0.0.1:1080`). The proxy is used for all Telegram Bot API requests, including startup webhook sync.

Manual webhook registration:

```powershell
Invoke-RestMethod -Uri "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<YOUR_PUBLIC_HTTPS_DOMAIN>/webhooks/telegram"
```

## Main Flows

- `POST /api/auth/telegram/init-data` validates Telegram `initData` and returns a session token.
- `POST /webhooks/telegram` handles `/start`, `/setup`, and Telegram chat poll answers.
- `POST /api/workspaces/{id}/events` creates and updates events.
- `POST /api/workspaces/{id}/polls` creates time-selection polls.
- The scheduler sends reminders and closes due polls.

## Tests

```powershell
.\.venv\Scripts\python -m pytest -q
```
