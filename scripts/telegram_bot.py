#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import ssl
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.config import settings

OPEN_APP_LABEL = "Открыть Mini App"
RESET_LABEL = "Очистить данные"
RESET_ACTION_LABEL = "Сбросить onboarding"
POLL_TIMEOUT_SECONDS = 30
RETRY_DELAY_SECONDS = 3
DEFAULT_RUNTIME_URL_FILE = REPO_ROOT / ".codex-runtime" / "backend-tunnel-url.txt"

shutdown_requested = False


def telegram_ssl_context() -> ssl.SSLContext:
    insecure = os.environ.get("TELEGRAM_API_INSECURE_SSL", "").strip().lower()
    if insecure in {"1", "true", "yes", "on"}:
        return ssl._create_unverified_context()
    return ssl.create_default_context()


def normalize_username(value: str | None) -> str | None:
    username = str(value or "").strip().lstrip("@")
    return username or None


def api_request(method: str, payload: dict[str, Any] | None = None, *, timeout: int = 10) -> Any:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не настроен.")

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}"
    data = None
    headers = {}
    http_method = "GET"

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
        http_method = "POST"

    req = request.Request(url, data=data, headers=headers, method=http_method)

    try:
        with request.urlopen(req, timeout=timeout, context=telegram_ssl_context()) as response:
            raw_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram API {method} вернул {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Не удалось связаться с Telegram API: {exc.reason}") from exc

    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Некорректный ответ Telegram API {method}: {raw_body}") from exc

    if not parsed.get("ok"):
        raise RuntimeError(f"Telegram API {method} завершился ошибкой: {parsed}")

    return parsed.get("result")


def resolve_bot_username() -> str:
    username = normalize_username(settings.telegram_bot_username)
    if username:
        return username

    me = api_request("getMe")
    username = normalize_username(me.get("username"))
    if not username:
        raise RuntimeError("Не удалось определить username бота. Укажите TELEGRAM_BOT_USERNAME.")
    return username


def build_open_app_url(bot_username: str) -> str:
    return f"https://t.me/{bot_username}/app"


def build_reset_url(bot_username: str) -> str:
    return f"https://t.me/{bot_username}/app?startapp=reset_onboarding"


def resolve_miniapp_public_url() -> str:
    explicit_url = os.environ.get("MINIAPP_PUBLIC_URL", "").strip()
    if explicit_url:
        return explicit_url

    configured_url = str(settings.miniapp_public_url or "").strip()
    if configured_url:
        return configured_url

    try:
        runtime_url = DEFAULT_RUNTIME_URL_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        runtime_url = ""

    if runtime_url:
        return runtime_url

    raise RuntimeError(
        "MINIAPP_PUBLIC_URL не настроен и локальный tunnel URL не найден. "
        "Сначала подними Mini App stack или укажи MINIAPP_PUBLIC_URL."
    )


def build_reset_webapp_url() -> str:
    raw_url = resolve_miniapp_public_url()

    parts = urlsplit(raw_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["reset_onboarding"] = "1"
    next_query = urlencode(query)
    return urlunsplit((parts.scheme, parts.netloc, parts.path or '/', next_query, parts.fragment))


def build_reply_keyboard() -> dict[str, object]:
    return {
        "keyboard": [
            [
                {
                    "text": OPEN_APP_LABEL,
                    "web_app": {"url": resolve_miniapp_public_url()},
                }
            ],
            [{"text": RESET_LABEL}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def build_reset_inline_keyboard(bot_username: str) -> dict[str, list[list[dict[str, str]]]]:
    del bot_username
    return {
        "inline_keyboard": [
            [{"text": RESET_ACTION_LABEL, "web_app": {"url": build_reset_webapp_url()}}],
        ]
    }


def build_welcome_text(bot_username: str) -> str:
    public_url = resolve_miniapp_public_url()
    return (
        "Kinematics Mini App готов.\n\n"
        "Кнопка «Открыть Mini App» открывает приложение.\n"
        "Кнопка «Очистить данные» подготавливает сброс onboarding для текущего Telegram-пользователя.\n\n"
        f"Текущий Mini App URL:\n{public_url}\n\n"
        "Если нужен прямой deep link:\n"
        f"{build_open_app_url(bot_username)}"
    )


def build_reset_text() -> str:
    return (
        "Подготовил сброс onboarding.\n\n"
        "Нажми кнопку «Сбросить onboarding». Mini App откроется, очистит onboarding и вернёт вас к первому интервью.\n\n"
        "После успешной очистки бот пришлёт подтверждение в этот чат."
    )


def set_bot_commands() -> None:
    api_request(
        "setMyCommands",
        {
            "commands": [
                {"command": "start", "description": "Открыть меню Mini App"},
            ]
        },
    )


def send_message(chat_id: int, text: str, reply_markup: dict[str, Any]) -> None:
    api_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": reply_markup,
        },
    )


def extract_command(text: str | None) -> str:
    raw = str(text or "").strip()
    if not raw.startswith("/"):
        return raw.lower()
    command = raw.split(maxsplit=1)[0]
    return command.split("@", maxsplit=1)[0].lower()


def handle_message(message: dict[str, Any], bot_username: str) -> None:
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not isinstance(chat_id, int):
        return

    if chat.get("type") not in {"private", None}:
        return

    raw_text = str(message.get("text") or "").strip()
    command = extract_command(raw_text)

    if raw_text == RESET_LABEL:
        send_message(
            chat_id,
            build_reset_text(),
            build_reset_inline_keyboard(bot_username),
        )
        return

    if command == "/start":
        send_message(
            chat_id,
            build_welcome_text(bot_username),
            build_reply_keyboard(),
        )
        return

    send_message(
        chat_id,
        build_welcome_text(bot_username),
        build_reply_keyboard(),
    )


def request_updates(offset: int | None) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {
        "timeout": POLL_TIMEOUT_SECONDS,
        "allowed_updates": ["message"],
    }
    if offset is not None:
        payload["offset"] = offset
    result = api_request("getUpdates", payload, timeout=POLL_TIMEOUT_SECONDS + 5)
    return result if isinstance(result, list) else []


def stop_requested(signum: int, frame: Any) -> None:
    del signum, frame
    global shutdown_requested
    shutdown_requested = True


def main() -> int:
    signal.signal(signal.SIGINT, stop_requested)
    signal.signal(signal.SIGTERM, stop_requested)

    try:
        bot_username = resolve_bot_username()
        set_bot_commands()
    except Exception as exc:  # pragma: no cover - startup errors are terminal
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Telegram bot polling started for @{bot_username}")
    next_offset: int | None = None

    while not shutdown_requested:
        try:
            updates = request_updates(next_offset)
            for update in updates:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    next_offset = update_id + 1
                message = update.get("message")
                if isinstance(message, dict):
                    handle_message(message, bot_username)
        except Exception as exc:  # pragma: no cover - runtime resiliency
            print(str(exc), file=sys.stderr)
            time.sleep(RETRY_DELAY_SECONDS)

    print("Telegram bot polling stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
