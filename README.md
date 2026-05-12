# Telegram Scheduler Mini App

Telegram Scheduler Mini App - это единый сервис для планирования событий в Telegram-группах и личной Mini App. Проект объединяет FastAPI backend, Telegram-бота, React Mini App, SQLite-хранилище, фоновые задачи, голосования за время встречи и интеграции с внешними календарями.

Документация описывает актуальную версию проекта, которая находится на сервере в `/home/user1/tgminiapp`.

## Что умеет проект

- Авторизация пользователя через Telegram Mini App `initData`.
- Работа с рабочими пространствами, связанными с Telegram-чатами.
- Добавление бота в группу и подключение общего календаря чата.
- Управление владельцем и администраторами рабочих пространств.
- Создание, редактирование, удаление и завершение событий.
- Создание голосований за варианты времени.
- Синхронизация ответов из Telegram poll в базу приложения.
- Автоматическое создание события после завершения голосования.
- Досрочное завершение голосования, когда проголосовали все участники.
- Фоновое закрытие просроченных и готовых голосований без открытой Mini App.
- Удаление голосований из Mini App администратором.
- Напоминания и уведомления через Telegram.
- Подключение Google Calendar через OAuth.
- Загрузка ближайших Google Calendar событий пользователя на главный экран Mini App.
- Визуальная пометка импортированных Google событий синей полосой и меткой `Google`.
- Базовая поддержка Yandex Calendar через CalDAV/OAuth-заготовку.

## Архитектура

Проект разворачивается как один backend-сервис. Этот сервис одновременно обслуживает API, Telegram webhook, статику Mini App и фоновые задачи.

```text
apps/
  miniapp/                         React + TypeScript + Vite Mini App
    src/
      api.ts                       клиент API
      app.tsx                      маршрутизация Mini App
      pages/                       экраны приложения
      components/                  UI-компоненты
      styles/                      CSS
  server/
    scheduler_app/
      api/                         HTTP API routes
      bot/                         Telegram handlers и bot helpers
      core/                        settings, database, deps, security
      domain/                      SQLAlchemy models и Pydantic schemas
      integrations/                Google и Yandex providers
      services/                    бизнес-логика
      static/app/                  собранный frontend bundle

data/                              runtime SQLite база
.github/workflows/                 GitHub Actions
pyproject.toml                     backend package и зависимости
README.md                          документация проекта
```

## Технологии

Backend:

- Python 3.13+
- FastAPI
- Uvicorn
- aiogram 3
- SQLAlchemy async
- SQLite через `aiosqlite`
- Pydantic Settings
- httpx
- cryptography
- caldav и icalendar

Frontend:

- React 19
- TypeScript
- Vite
- React Router
- Telegram Mini Apps SDK

Хранилище:

- По умолчанию SQLite: `data/app.db`.
- Можно заменить через `DATABASE_URL`.

## Основные сущности

### User

Пользователь приложения. Обычно создается из Telegram-аккаунта. Хранит Telegram ID, username, имя, фамилию и язык.

### TelegramChat

Telegram-чат, к которому подключен бот. Используется для связи группы и рабочего пространства.

### Workspace

Рабочее пространство календаря. Может быть личным или связанным с Telegram-группой. Внутри workspace находятся события, голосования и участники.

### WorkspaceMember

Связь пользователя с workspace. Роли:

- `owner` - владелец, может управлять администраторами.
- `admin` - может создавать и управлять событиями/голосованиями.
- `member` - обычный участник.

### Event

Событие календаря. Содержит название, описание, место, время начала и окончания, часовой пояс, участников, статус и источник.

Статусы:

- `scheduled`
- `cancelled`
- `completed`

Источники:

- `manual` - создано вручную.
- `poll` - создано из голосования.

### Poll

Голосование за время события. Содержит варианты времени, дедлайн, участников, голоса, статус и ссылку на созданное событие.

Статусы:

- `open` - голосование открыто.
- `finalized` - завершено, событие создано.
- `needs_admin_resolution` - ничья или нет победителя, нужен выбор администратора.
- `cancelled` - отменено.

### CalendarConnection

Подключение пользователя к внешнему календарю. Сейчас используется для Google Calendar и Yandex Calendar. Токены шифруются через `APP_SECRET`.

## Переменные окружения

Файл примера: `.env.example`.

```env
APP_ENV=production
BASE_URL=https://your-domain.example
APP_SECRET=replace-me
BOT_TOKEN=123456:replace-me
BOT_USERNAME=replace-me
TELEGRAM_PROXY_URL=socks5://127.0.0.1:1080
TELEGRAM_UPDATES_MODE=webhook
TELEGRAM_REQUEST_TIMEOUT_SECONDS=6
ALLOW_INSECURE_DEV_AUTH=false
SYNC_TELEGRAM_WEBHOOK_ON_STARTUP=true
SCHEDULER_INTERVAL_SECONDS=300
DATABASE_URL=
SQLITE_PATH=data/app.db
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
YANDEX_CLIENT_ID=
YANDEX_CLIENT_SECRET=
YANDEX_SCOPES=
```

### Обязательные настройки production

- `APP_ENV=production`
- `BASE_URL` - публичный HTTPS URL сервера.
- `APP_SECRET` - длинный секрет для сессий и шифрования токенов календарей.
- `BOT_TOKEN` - токен Telegram-бота.
- `BOT_USERNAME` - username Telegram-бота без `@`.
- `ALLOW_INSECURE_DEV_AUTH=false`

### Telegram настройки

- `TELEGRAM_UPDATES_MODE=webhook` - production-режим через webhook.
- `TELEGRAM_UPDATES_MODE=polling` - альтернативный режим long polling.
- `SYNC_TELEGRAM_WEBHOOK_ON_STARTUP=true` - приложение само выставляет webhook при старте.
- `TELEGRAM_PROXY_URL` - SOCKS/HTTP proxy для Telegram API, если сервер не ходит напрямую в Telegram.
- `TELEGRAM_REQUEST_TIMEOUT_SECONDS` - timeout запросов к Telegram API.

### Google Calendar настройки

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

В Google Cloud Console нужно добавить redirect URI:

```text
https://<BASE_URL>/oauth/google/callback
```

Scopes проекта:

```text
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/userinfo.email
```

### Yandex Calendar настройки

- `YANDEX_CLIENT_ID`
- `YANDEX_CLIENT_SECRET`
- `YANDEX_SCOPES`

Redirect URI:

```text
https://<BASE_URL>/oauth/yandex/callback
```

## Установка backend

На сервере:

```bash
cd /home/user1/tgminiapp
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

Если Python 3.13 доступен как `python3`, можно использовать его:

```bash
python3 -m venv .venv
```

## Установка frontend

```bash
cd /home/user1/tgminiapp/apps/miniapp
npm install
npm run build
```

Команда `npm run build` собирает Mini App с base path `/app/` и кладет результат в backend static directory `apps/server/scheduler_app/static/app`.

## Запуск приложения

Из корня проекта:

```bash
cd /home/user1/tgminiapp
. .venv/bin/activate
python -m uvicorn scheduler_app.main:app --host 0.0.0.0 --port 8000
```

Или через entrypoint пакета:

```bash
telegram-scheduler
```

Проверка:

```bash
curl http://127.0.0.1:8000/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

Mini App доступна по адресу:

```text
https://<BASE_URL>/app
```

## Production deployment

Типовая схема production:

1. Код лежит в `/home/user1/tgminiapp`.
2. Python-зависимости установлены в `.venv`.
3. Frontend собран в `apps/server/scheduler_app/static/app`.
4. Backend запущен как systemd-service или другим process manager.
5. Перед FastAPI стоит nginx или другой reverse proxy с HTTPS.
6. `BASE_URL` указывает на публичный HTTPS домен.
7. Telegram webhook указывает на `https://<BASE_URL>/webhooks/telegram`.

Пример команды ручного рестарта зависит от имени сервиса на сервере. Если сервис называется `tgminiapp`, то:

```bash
sudo systemctl restart tgminiapp
sudo systemctl status tgminiapp --no-pager
```

## Telegram Bot

### Личные команды

- `/start` - открыть Mini App, добавить бота в чат, перейти к администрированию чатов, подключить Google.
- `/admins` - управление администраторами рабочих пространств, где пользователь является владельцем.

### Групповые команды

- `/setup` - подключить календарь чата.
- `/connect` - подключиться к календарю чата.
- `/join` - подключиться к календарю чата.

### Подключение группы

1. Пользователь добавляет бота в Telegram-группу.
2. В группе вызывается `/setup` или нажимается кнопка подключения.
3. Первый обычный пользователь, подключивший календарь чата, становится владельцем workspace.
4. Остальные участники подключаются через кнопку или команду.
5. Владелец может назначать администраторов через `/admins` в личке бота.

## Mini App

Основные экраны:

- Главный экран dashboard.
- Создание и редактирование события.
- Создание голосования.
- Просмотр голосования.
- Интеграции календарей.

### Главный экран

На главном экране пользователь видит:

- текущий день;
- выбранное workspace;
- ближайшие события workspace;
- ближайшие события из Google Calendar, если Google подключен;
- открытые голосования;
- статус календарных интеграций.

События сортируются по времени наступления. События, пришедшие из Google Calendar и отсутствующие как локальные события workspace, помечаются синей полоской и меткой `Google`.

Список событий прокручивается: сначала видны ближайшие карточки, остальные доступны через scroll.

### События

Администратор workspace может:

- создать событие;
- выбрать участников;
- указать название, описание, место, дату, время и часовой пояс;
- отредактировать событие;
- удалить событие;
- отметить событие завершенным.

### Голосования

Администратор workspace может создать голосование за время события:

1. Указывает название, описание и дедлайн.
2. Добавляет варианты времени.
3. Выбирает участников.
4. Если workspace связан с Telegram-группой, бот публикует Telegram poll в чат.
5. Участники голосуют в Telegram poll или Mini App, в зависимости от типа голосования.
6. Когда все участники проголосовали, голосование завершается сразу, без ожидания дедлайна.
7. Если есть единственный победитель, создается событие.
8. Если победителя нет или есть ничья, статус становится `needs_admin_resolution`, администратор выбирает итоговый вариант вручную.

Голосование можно удалить из Mini App. При удалении приложение пытается закрыть связанный Telegram poll и очищает связь с созданным событием.

## Google Calendar

### Подключение

1. Пользователь открывает Mini App.
2. Переходит к интеграциям или нажимает кнопку подключения Google.
3. Backend создает OAuth URL через `POST /api/integrations/google/connect`.
4. Пользователь проходит Google OAuth.
5. Google возвращает пользователя на `/oauth/google/callback`.
6. Backend сохраняет подключение и шифрует access/refresh tokens.

### Отображение событий

После подключения Google Mini App запрашивает:

```text
GET /api/integrations/google/events
```

Backend получает ближайшие события из Google Calendar пользователя. На dashboard они смешиваются с локальными событиями workspace и сортируются по `start_at`.

Google-события не превращаются автоматически в локальные `Event`. Они отображаются как внешние календарные события, чтобы пользователь видел свой реальный календарь на главном экране.

## Yandex Calendar

В проекте есть provider для Yandex Calendar. Он использует OAuth-настройки и календарную интеграцию через CalDAV. Текущая основная пользовательская интеграция в интерфейсе сфокусирована на Google Calendar.

## API

Все основные API доступны под префиксом `/api`.

### Auth

```text
POST /api/auth/telegram/init-data
GET  /api/me
```

`POST /api/auth/telegram/init-data` проверяет Telegram Mini App `initData` и возвращает session token.

### Workspaces

```text
GET  /api/workspaces
POST /api/workspaces/{workspace_id}/join
```

### Events

```text
GET    /api/workspaces/{workspace_id}/events
POST   /api/workspaces/{workspace_id}/events
GET    /api/events/{event_id}
PATCH  /api/events/{event_id}
DELETE /api/events/{event_id}
POST   /api/events/{event_id}/complete
POST   /api/events/{event_id}/attendance
```

### Polls

```text
GET    /api/workspaces/{workspace_id}/polls
POST   /api/workspaces/{workspace_id}/polls
GET    /api/polls/{poll_id}
DELETE /api/polls/{poll_id}
POST   /api/polls/{poll_id}/vote
POST   /api/polls/{poll_id}/resolve
```

### Integrations

```text
GET   /api/integrations
POST  /api/integrations/google/connect
POST  /api/integrations/yandex/connect
GET   /api/integrations/google/events
PATCH /api/integrations/{connection_id}
```

### OAuth callbacks

```text
GET /oauth/google/callback
GET /oauth/yandex/callback
```

### Telegram webhook

```text
POST /webhooks/telegram
```

Webhook принимает Telegram updates, передает их в aiogram dispatcher и после обработки запускает scheduler tick.

## Фоновый scheduler

Scheduler запускается внутри FastAPI lifespan и выполняет:

- проверку открытых голосований, где уже проголосовали все участники;
- завершение голосований, у которых прошел дедлайн;
- отправку due notification jobs.

Даже если `SCHEDULER_INTERVAL_SECONDS=300`, фактический цикл ограничен максимум 15 секундами, чтобы готовые голосования закрывались без открытой Mini App.

Дополнительно scheduler запускается после активности API и после Telegram update. Это ускоряет реакцию приложения, но не является единственным механизмом завершения голосований.

## Уведомления

NotificationService отправляет сообщения пользователям через Telegram. Используется для:

- напоминаний о событиях;
- уведомлений о создании/изменении/удалении событий;
- завершения голосований;
- ситуации, когда голосование завершилось без победителя.

## База данных

По умолчанию база лежит здесь:

```text
data/app.db
```

Путь задается через `SQLITE_PATH`. Если указан `DATABASE_URL`, используется он.

Таблицы создаются автоматически при старте приложения через SQLAlchemy `Base.metadata.create_all`.

Важно: `data/*.db` и `data/*.sqlite3` не должны попадать в git.

## Сборка и проверка

### Backend tests

```bash
cd /home/user1/tgminiapp
. .venv/bin/activate
python -m pytest -q
```

### Python compile check

```bash
cd /home/user1/tgminiapp
. .venv/bin/activate
python -m compileall apps/server/scheduler_app
```

### Frontend build

```bash
cd /home/user1/tgminiapp/apps/miniapp
npm run build
```

## Git workflow

Перед изменениями:

```bash
cd /home/user1/tgminiapp
git status --short --branch
```

После изменений:

```bash
git add README.md
git commit -m "Update Russian project documentation"
git push origin main
```

Если GitHub main нужно принудительно сделать равным серверной версии:

```bash
git push --force origin main
```

Использовать force push нужно только когда серверная история действительно является приоритетной.

## Безопасность

- Не коммитить `.env`, реальные токены и production secrets.
- Если секрет уже попал в историю git, его нужно перевыпустить в соответствующем сервисе.
- `APP_SECRET` должен быть стабильным между рестартами, иначе сохраненные токены календарей могут стать нечитаемыми.
- В production держать `ALLOW_INSECURE_DEV_AUTH=false`.
- Для Telegram Mini App использовать только HTTPS `BASE_URL`.
- OAuth redirect URI в Google/Yandex должен точно совпадать с `BASE_URL`.

## Частые проблемы

### Mini App открывается, но API возвращает 401

Проверить:

- Mini App открыта внутри Telegram;
- backend получает корректный Telegram `initData`;
- `BOT_TOKEN` совпадает с ботом, через которого открывается Mini App;
- `ALLOW_INSECURE_DEV_AUTH=false` в production.

### Telegram webhook не работает

Проверить:

```bash
curl https://<BASE_URL>/health
```

Затем проверить:

- `BASE_URL` начинается с `https://`;
- `SYNC_TELEGRAM_WEBHOOK_ON_STARTUP=true`;
- сервер может достучаться до Telegram API напрямую или через `TELEGRAM_PROXY_URL`;
- webhook URL: `https://<BASE_URL>/webhooks/telegram`.

### Голосование не создает событие

Проверить:

- участники голосования входят в workspace;
- все участники проголосовали или прошел дедлайн;
- нет ничьей между вариантами;
- scheduler работает;
- Telegram poll answers доходят до webhook или polling loop;
- в логах нет ошибок Telegram API при `stop_poll` или отправке сообщений.

Если все проголосовали, событие должно создаваться без ожидания дедлайна.

### Google события не видны на главном экране

Проверить:

- пользователь подключил Google;
- `GOOGLE_CLIENT_ID` и `GOOGLE_CLIENT_SECRET` заданы;
- Google OAuth redirect URI совпадает с `/oauth/google/callback`;
- endpoint `GET /api/integrations/google/events` возвращает события;
- у событий Google есть будущий `start_at`.

### Frontend после деплоя не обновился

Пересобрать Mini App:

```bash
cd /home/user1/tgminiapp/apps/miniapp
npm run build
```

Затем перезапустить backend, если process manager кеширует файлы или окружение.

## Краткая карта файлов

- `apps/server/scheduler_app/main.py` - создание FastAPI app, Telegram webhook, static serving, scheduler lifecycle.
- `apps/server/scheduler_app/core/settings.py` - все env settings.
- `apps/server/scheduler_app/domain/models.py` - SQLAlchemy модели.
- `apps/server/scheduler_app/domain/schemas.py` - Pydantic request/response schemas.
- `apps/server/scheduler_app/api/routes/events.py` - API событий.
- `apps/server/scheduler_app/api/routes/polls.py` - API голосований.
- `apps/server/scheduler_app/api/routes/integrations.py` - API интеграций и OAuth callbacks.
- `apps/server/scheduler_app/bot/handlers.py` - команды Telegram и обработка poll answers.
- `apps/server/scheduler_app/services/polls.py` - логика голосований и создания события по итогам.
- `apps/server/scheduler_app/services/scheduler.py` - фоновый scheduler.
- `apps/server/scheduler_app/services/integrations.py` - подключение календарей.
- `apps/server/scheduler_app/integrations/google.py` - Google Calendar provider.
- `apps/miniapp/src/api.ts` - frontend API client.
- `apps/miniapp/src/pages/dashboard-home-page.tsx` - главный экран Mini App.
- `apps/miniapp/src/pages/poll-page.tsx` - экран голосования.
- `apps/miniapp/src/pages/integrations-page.tsx` - экран интеграций.

## Текущее состояние документации

Этот README заменяет старую краткую документацию и является основной русскоязычной документацией проекта.
