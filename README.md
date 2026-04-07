# Kinematics Deploy Copy

Чистая рабочая копия проекта для запуска из папки `деплой`.

## Структура

- `app/` — backend на FastAPI
- `frontend/` — frontend и vercel-конфиги
- `scripts/` — локальный bootstrap и вспомогательные команды
- `data/` — данные моделей, логов и отчетов
- `alembic/` и `alembic.ini` — миграции базы
- `DATABASE_URL` в `.env` — подключение к локальной PostgreSQL-базе

## Быстрый запуск

Перед bootstrap подними локальный Postgres и создай базу `kinematics`.
Дефолтный URL в проекте:

```bash
postgresql+psycopg://postgres:postgres@127.0.0.1:5432/kinematics
```

Пример для локального `psql`:

```bash
createdb kinematics
```

```bash
cd "/Users/galagozaevgenij/Documents/New project/деплой"
python3 scripts/dev_telegram_miniapp.py bootstrap
python3 scripts/dev_telegram_miniapp.py run --skip-bot
```

## Альтернативно

```bash
cd "/Users/galagozaevgenij/Documents/New project/деплой"
source .venv/bin/activate
make backend
```
