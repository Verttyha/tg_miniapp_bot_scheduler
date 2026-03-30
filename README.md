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

### 3. Publish localhost over HTTPS for Telegram

`ngrok` is no longer required. The default tunnel helper now uses `localhost.run`, because it has been more reliable in this environment than Cloudflare quick tunnels:

```powershell
.\telegram-scheduler-tunnel.cmd
```

`localhost.run` uses the system `ssh` client, so no extra tunnel binary is required on a standard Windows install with OpenSSH Client enabled.

There is also an installed console script on fresh environments: `.\.venv\Scripts\telegram-scheduler-tunnel`.

What this command does:

- starts an SSH reverse tunnel to `localhost.run`
- detects the generated public `https://...` URL
- writes that URL into `.env` as `BASE_URL`
- keeps the tunnel alive until you stop it

Keep that terminal open. If the backend is already running, restart it once so the app picks up the new `BASE_URL`.

When the backend starts with a public `https` `BASE_URL`, it now registers Telegram webhook automatically at `/webhooks/telegram`.

If you need the previous fallback explicitly, you can still use Cloudflare:

```powershell
.\telegram-scheduler-cloudflare.cmd --protocol http2
```

### 4. Rebuild the Mini App only if needed

You only need to rebuild the frontend if you changed files inside `apps/miniapp`. A built frontend bundle is already present in `apps/server/scheduler_app/static/app`.

```powershell
Set-Location apps\miniapp
cmd /c npm install
cmd /c npm run build
Set-Location ..\..
```

### 5. Ready-to-run commands for this workspace

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

Start the public HTTPS tunnel:

```powershell
cd C:\Users\andre\Desktop\tgbotminiapp\tg_miniapp_bot_teacher
.\telegram-scheduler-tunnel.cmd
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
- when `BASE_URL` points to a public `https` address, the app syncs the webhook automatically on startup

If you disable `SYNC_TELEGRAM_WEBHOOK_ON_STARTUP`, you can still register the webhook manually:

```powershell
Invoke-RestMethod -Uri "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<YOUR_PUBLIC_HTTPS_DOMAIN>/webhooks/telegram"
```

`BASE_URL` in `.env` must match the same public address.

## Why Not Vercel?

Vercel is a good fit for hosting the static Mini App frontend, but it is a poor drop-in replacement for the local development tunnel in this repository because the project currently depends on:

- a local FastAPI process receiving Telegram webhooks
- SQLite on the local filesystem
- an in-process scheduler for reminders and poll finalization

For this stack, exposing the existing local service through a lightweight public tunnel is the smallest and safest change. The default helper now uses `localhost.run`, with Cloudflare still available as a fallback provider.

## Main Flows

- `POST /api/auth/telegram/init-data` validates Telegram `initData` and returns a signed session token
- `POST /webhooks/telegram` handles `/start` in private chat, offers opening the Mini App, and provides an "add to chat" deep link
- `POST /webhooks/telegram` handles `/start` and `/setup` in groups, creating the workspace automatically after the bot is added
- `POST /api/workspaces/{id}/events` creates events and fans them out to active participant calendars
- `POST /api/workspaces/{id}/polls` creates vote-based scheduling polls and publishes them as native Telegram polls in the linked chat
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

.\telegram-scheduler-tunnel.cmd
```
