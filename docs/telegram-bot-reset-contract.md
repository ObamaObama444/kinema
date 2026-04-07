# Telegram Bot Reset Contract

## Что должно делать действие `Очистить данные`
- Бот не вызывает backend reset напрямую.
- Бот открывает Mini App deep link со `startapp` параметром:
  - `https://t.me/<bot_username>/app?startapp=reset_onboarding`

## Что уже реализовано в Mini App
- `Telegram.WebApp.initDataUnsafe.start_param` читается на frontend.
- Если стартовый параметр равен `reset_onboarding`, Mini App сохраняет pending-флаг в `sessionStorage`.
- После авторизации Mini App сам вызывает `POST /api/onboarding/reset`.
- Reset очищает только ответы onboarding и флаг завершения.
- Аккаунт, cookie-сессия, история тренировок, активная программа и существующие данные профиля не удаляются.

## Ожидаемое поведение
1. Пользователь нажимает в боте `Очистить данные`.
2. Открывается Mini App через deep link со `startapp=reset_onboarding`.
3. Если пользователь уже авторизован, onboarding очищается сразу.
4. Если пользователь не авторизован, сначала проходит login, затем reset выполняется один раз.
5. После reset открывается onboarding-сценарий с первого экрана.

## Bot runner в этом репозитории
- Добавлен polling-скрипт [scripts/telegram_bot.py](/Users/galagozaevgenij/Documents/New%20project/scripts/telegram_bot.py).
- Команда запуска:
```bash
cd "/Users/galagozaevgenij/Documents/New project"
make telegram-bot
```
- На `/start` бот отправляет две inline-кнопки:
  - `Открыть Mini App`
  - `Очистить данные`
- Кнопка `Очистить данные` открывает:
  - `https://t.me/<bot_username>/app?startapp=reset_onboarding`
