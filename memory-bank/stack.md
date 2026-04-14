# Stack

- Backend: FastAPI, aiogram, SQLAlchemy async
- Telegram event sync: aiogram `my_chat_member` updates for bot membership changes (`left`/`kicked`)
- Group onboarding UX: inline Telegram keyboard with callback buttons `Подключиться` / `Вступить` for chat membership flow
- Frontend: React, TypeScript, Vite, Telegram Mini Apps SDK
- Session identity source: Telegram `initData` bootstrap on each Mini App launch (token is refreshed from backend response)
- Frontend structure: route pages + reusable components + hooks + lib helpers + layered CSS imports
- Storage: SQLite by default, optional `DATABASE_URL` override
- Integrations: Google Calendar REST, Yandex Calendar via CalDAV
- Runtime: one Python process for API, webhook handling, scheduler, and static Mini App serving
- Frontend theme: dark Telegram-friendly dashboard layout
