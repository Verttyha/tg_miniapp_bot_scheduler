# Progress

## 2026-04-03

- removed tunnel helper scripts and backend tunnel package
- removed generated local artifacts from the repository tree
- introduced backend `core` and `domain` directories
- kept the dark Mini App dashboard as the default home route
- added `docs.me` with a full repository map
- restored `memory-bank` as a tracked project directory
- split the Mini App frontend into `pages`, `components`, `hooks`, `lib`, and layered `styles`
- verified the frontend refactor with a successful `npm run build`, then removed temporary `node_modules` and generated assets again
- added Telegram `my_chat_member` handling to detach removed group chats from active workspaces
- added integration test for `/setup` -> bot removed (`my_chat_member`) -> workspace hidden from `/api/me`

## 2026-04-14

- replaced group onboarding command hint with inline actions `Подключиться` / `Вступить`
- added welcome message with connect buttons when bot is added to a group
- added callback flow (`workspace:connect`) to join users to group workspace without manual `/start@...`
- updated Mini App empty-state hint to reflect button-based group onboarding
- added tests for welcome buttons and callback-based group join
