# System Patterns

- FastAPI serves both API routes and the built Mini App.
- Aiogram handles Telegram updates through a webhook endpoint.
- Business logic is organized in `services`.
- Runtime primitives live in `core`.
- Models and schemas live in `domain`.
- Scheduler work runs in-process for reminders and poll resolution.

