# Telegram Mini App Setup

## После git clone
Теперь есть локальный сценарий без `Vercel` и без ручного подъёма трёх терминалов.

Достаточно:
```bash
cd "/Users/galagozaevgenij/Documents/New project"
make tg-miniapp
```

Что сделает команда:
1. создаст `.env` из `.env.example`, если его ещё нет
2. поднимет `.venv`
3. установит Python-зависимости
4. прогонит `alembic upgrade head`
5. запустит локальный `FastAPI`
6. поднимет публичный `localhost.run` tunnel
7. если в `.env` заполнен `TELEGRAM_BOT_TOKEN`, автоматически поднимет polling-бота

Что нужно для запуска именно в Telegram:
- указать `TELEGRAM_BOT_TOKEN` в `.env`
- желательно указать `TELEGRAM_BOT_USERNAME`, чтобы launcher сразу печатал прямую ссылку на бота

После старта:
- в терминале появится `Mini App URL`
- если бот запущен, открой чат с ботом и отправь `/start`
- бот пришлёт кнопку `Открыть Mini App`

Если bot token пока не настроен, команда всё равно поднимет backend и публичный URL. Это удобно, чтобы быстро проверить локальный стек и потом уже докинуть Telegram credentials.

Если `8000` уже занят другим процессом:
```bash
cd "/Users/galagozaevgenij/Documents/New project"
BACKEND_PORT=8100 make tg-miniapp
```

## Что уже сделано
- `frontend/` подготовлен как статический Vercel frontend.
- Все запросы с frontend идут на относительные `/api/*` и `/static/*`.
- `frontend/vercel.json` проксирует production-трафик в локальный FastAPI backend через production tunnel.
- `frontend/vercel.dev.json` нужен только для разработки, чтобы фронт ходил в локальный backend без правки production-конфига.
- Backend остаётся локальным: SQLite, локальные файлы, локальные логи.
- В `Makefile` добавлены короткие команды запуска и синхронизации backend tunnel URL.

## Канонический tunnel
- Для сценария `git clone -> make tg-miniapp` launcher использует `localhost.run`, чтобы не требовать отдельную установку `ngrok`.
- Для production/Vercel-потока канонический tunnel по-прежнему `ngrok`.
- В `BotFather` для production по-прежнему указывается только `https://YOUR_PROJECT.vercel.app/`, а не tunnel URL.

## Канонический Telegram-режим
Этот режим остаётся для production-потока через `Vercel`, но для запуска после клона теперь лучше использовать `make tg-miniapp`.

Терминал 1:
```bash
cd "/Users/galagozaevgenij/Documents/New project"
make backend-stable
```

Терминал 2:
```bash
cd "/Users/galagozaevgenij/Documents/New project"
make backend-tunnel
```

Терминал 3:
```bash
cd "/Users/galagozaevgenij/Documents/New project"
make deploy-miniapp
```

После этого:
1. `make backend-tunnel` поднимет `ngrok` для `127.0.0.1:8000`
2. `make deploy-miniapp` сам возьмёт живой `https://...ngrok...` из локального `ngrok API`, проверит `/health`, обновит `frontend/vercel.json` и задеплоит Vercel
3. В `BotFather` остаётся production URL вида `https://YOUR_PROJECT.vercel.app/`
4. Открываешь бота на телефоне и запускаешь Mini App

Что важно:
- перед обновлением `frontend/vercel.json` script всегда проверяет живость tunnel через `/health`
- если хочешь подставить URL вручную, можно так:
```bash
BACKEND_TUNNEL_URL=https://YOUR_BACKEND_TUNNEL_HOST make sync-backend-url
```

## Быстрый browser/dev режим
Для локальной верстки без production deploy можно по-прежнему использовать:
```bash
make backend
make frontend-dev
make frontend-tunnel
```

Но это не лучший режим для Telegram, потому что Mini App должен ходить через production `Vercel` URL.

## Настроить Mini App URL в BotFather
В BotFather:
- открыть бота
- настроить Mini App / Web App URL
- указать production `Vercel` URL:
```text
https://YOUR_VERCEL_PROJECT.vercel.app/
```

Не указывай здесь прямой tunnel URL, если хочешь открыть Mini App без промежуточного окна.

Для локального dev-режима через `make tg-miniapp` это не обязательно: можно просто открыть чат с ботом и использовать reply-кнопку, которую отправляет `scripts/telegram_bot.py`.

## Smoke-check login и защищённого API
Открыть Mini App URL в браузере или Telegram.

Ожидаемый flow:
1. Открывается `/`
2. Launcher проверяет `/api/auth/me`
3. Если сессии нет, редиректит на `/login`
4. После login backend ставит cookies
5. Frontend открывает `/app`
6. Защищённые запросы идут через proxy в backend

Для ручной проверки production:
```bash
curl -i https://YOUR_VERCEL_URL/api/auth/me
curl -i https://YOUR_VERCEL_URL/health
```

## Проверка стека
```bash
cd "/Users/galagozaevgenij/Documents/New project"
make miniapp-status
```

Команда покажет:
- локальный `backend /health`
- URL из `.codex-runtime/backend-tunnel-url.txt`
- публичный `https://frontend-nine-psi-85.vercel.app/health`

## Если production tunnel URL поменялся
1. Подними новый backend tunnel
2. Выполни:
```bash
cd "/Users/galagozaevgenij/Documents/New project"
make deploy-miniapp
```
3. Если `sync-backend-url` не может прочитать runtime URL file, подставь URL вручную:
```bash
cd "/Users/galagozaevgenij/Documents/New project"
BACKEND_TUNNEL_URL=https://YOUR_BACKEND_TUNNEL_HOST make deploy-miniapp
```
4. Backend и SQLite трогать не нужно

## Замечания
- Bot token не хранится во frontend.
- Локальная SQLite остаётся на Mac.
- CORS не нужен как основной механизм, потому что frontend использует same-origin запросы через Vercel rewrites.
- Текущая email/password auth остаётся без переписывания на Telegram auth на этом шаге.
- Для Telegram без предупреждения используй `Vercel` URL как точку входа.
- Для production deploy-потока `ngrok` остаётся каноническим tunnel.
- Для локального сценария после клона launcher использует `localhost.run`, потому что он поднимается без отдельной установки.
- Для локального сценария после клона `MINIAPP_PUBLIC_URL` можно не заполнять вручную: `make tg-miniapp` пробросит актуальный tunnel URL в бота сам.

## Reset onboarding через бота
- Контракт для bot-side кнопки описан в [telegram-bot-reset-contract.md](./telegram-bot-reset-contract.md).
- Mini App уже умеет обрабатывать `startapp=reset_onboarding` и выполнять `POST /api/onboarding/reset` после авторизации.
