# Telegram Scheduler Mini App

Telegram Mini App and Telegram bot for collaborative schedule management, event voting, calendar sync, reminders, and attendance tracking.

The project combines in a single service:

- FastAPI API
- Telegram bot webhook handlers
- React Mini App served by the same process
- SQLite persistence
- Google and Yandex calendar integration adapters
- In-process scheduler for reminders and poll auto-resolution

## Stack

- Backend: FastAPI, aiogram, SQLAlchemy async, SQLite
- Frontend: React, TypeScript, Vite, Telegram Mini Apps SDK
- Integrations: Google Calendar REST, Yandex Calendar CalDAV adapter

## Quick Start

This is the minimal PowerShell flow to start the service locally.

### 1. Prepare the environment

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .[dev]
Copy-Item .env.example .env
```

Then open `.env` and fill at least:

- `APP_SECRET`
- `BOT_TOKEN`
- `BOT_USERNAME`
- `BASE_URL`

For local startup you can keep:

```env
BASE_URL=http://localhost:8000
```

### 2. Start the bot and API

Main quick-start command:

```powershell
.\.venv\Scripts\telegram-scheduler
```

Alternative via `uvicorn`:

```powershell
.\.venv\Scripts\python -m uvicorn scheduler_app.main:app --reload
```

After startup:

- Mini App: [http://localhost:8000/app](http://localhost:8000/app)
- Healthcheck: [http://localhost:8000/health](http://localhost:8000/health)

### 3. Rebuild the Mini App only if needed

You only need to rebuild the frontend if you changed files inside `apps/miniapp`. A built frontend bundle is already present in `apps/server/scheduler_app/static/app`.

```powershell
Set-Location apps\miniapp
cmd /c npm install
cmd /c npm run build
Set-Location ..\..
```

### 4. Ready-to-run commands for this workspace

Use these exact commands for `C:\Users\andre\Desktop\tgbotminiapp\tg_miniapp_bot_teacher`.

Build the Mini App:

```powershell
cd C:\Users\andre\Desktop\tgbotminiapp\tg_miniapp_bot_teacher\apps\miniapp
cmd /c npm run build
```

Run the backend on `127.0.0.1:8000`:

```powershell
cd C:\Users\andre\Desktop\tgbotminiapp\tg_miniapp_bot_teacher
.\.venv\Scripts\python -m uvicorn scheduler_app.main:app --host 127.0.0.1 --port 8000 --reload
```

Start ngrok for port `8000`:

```powershell
ngrok http 8000
```

## Quick Bot Launch Commands

If dependencies are already installed and `.env` is configured, one command is enough:

```powershell
.\.venv\Scripts\telegram-scheduler
```

If this is the first launch, use:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
Copy-Item .env.example .env
.\.venv\Scripts\telegram-scheduler
```

## Important: Telegram Webhook

This bot receives Telegram updates through webhook `POST /webhooks/telegram`.

That means:

- the service starts locally without issues
- Telegram cannot deliver updates to `localhost`
- a real bot setup needs a public `https` URL in `BASE_URL`

Example webhook setup command:

```powershell
Invoke-RestMethod -Uri "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<YOUR_PUBLIC_HTTPS_DOMAIN>/webhooks/telegram"
```

`BASE_URL` in `.env` must match the same public address.

## Main Flows

- `POST /api/auth/telegram/init-data` validates Telegram `initData` and returns a signed session token
- `POST /webhooks/telegram` handles `/start` in private chat and `/setup` in groups
- `POST /api/workspaces/{id}/events` creates events and fans them out to active participant calendars
- `POST /api/workspaces/{id}/polls` creates vote-based scheduling polls
- In-process scheduler finalizes due polls and sends due reminders

## Tests

```powershell
.\.venv\Scripts\python -m pytest -q
```

```powershell
cd C:\Users\andre\Desktop\tgbotminiapp\tg_miniapp_bot_teacher\apps\miniapp
cmd /c npm run build

cd C:\Users\andre\Desktop\tgbotminiapp\tg_miniapp_bot_teacher
.\.venv\Scripts\python -m uvicorn scheduler_app.main:app --host 127.0.0.1 --port 8000 --reload

ngrok http 8000
```
