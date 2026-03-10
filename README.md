# Telegram Scheduler Mini App

Single-service Telegram scheduler that combines:

- FastAPI API
- Telegram bot webhook handlers
- React Mini App served by the same process
- SQLite persistence
- Google/Yandex calendar integration adapters
- In-process scheduler for reminders and poll auto-resolution

## Stack

- Backend: FastAPI, aiogram, SQLAlchemy async, SQLite
- Frontend: React, TypeScript, Vite, Telegram Mini Apps SDK
- Integrations: Google Calendar REST, Yandex Calendar CalDAV adapter

## Quick Start

1. Create and activate a virtual environment.
2. Install Python dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
```

3. Install Mini App dependencies:

```powershell
Set-Location apps\miniapp
cmd /c npm install
cmd /c npm run build
Set-Location ..\..
```

4. Copy `.env.example` to `.env` and fill in at least:

- `APP_SECRET`
- `BOT_TOKEN`
- `BOT_USERNAME`
- `BASE_URL`

5. Run the service:

```powershell
.\.venv\Scripts\python -m uvicorn scheduler_app.main:app --reload
```

6. Open the Mini App shell:

- Local: [http://localhost:8000/app](http://localhost:8000/app)

## Main Flows

- `POST /api/auth/telegram/init-data` validates Telegram `initData` and returns a signed session token.
- `POST /webhooks/telegram` handles `/start` in private chat and `/setup` in groups.
- `POST /api/workspaces/{id}/events` creates events and fans them out to active participant calendars.
- `POST /api/workspaces/{id}/polls` creates vote-based scheduling polls.
- In-process scheduler finalizes due polls and sends due reminders.

## Testing

```powershell
.\.venv\Scripts\python -m pytest -q
```

## Notes

- SQLite is intended for a single-instance deployment.
- The Figma file is still pending access; current UI is requirements-based.
- Memory Bank files are committed under `memory-bank/` because the MCP Memory Bank path initialization is currently failing on this Windows setup.
