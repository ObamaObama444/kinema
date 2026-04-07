from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from urllib import parse, request


class TelegramInitDataError(ValueError):
    pass


def parse_telegram_user_without_validation(init_data: str) -> dict[str, object]:
    if not init_data:
        raise TelegramInitDataError("Telegram init data отсутствуют.")

    pairs = parse.parse_qsl(init_data, keep_blank_values=True)
    payload = dict(pairs)
    raw_user = payload.get("user")
    if not raw_user:
        raise TelegramInitDataError("В Telegram init data отсутствует user.")

    try:
        user = json.loads(str(raw_user))
    except json.JSONDecodeError as exc:
        raise TelegramInitDataError("Не удалось распарсить Telegram user.") from exc

    if not isinstance(user, dict):
        raise TelegramInitDataError("Некорректный Telegram user.")

    return user


def validate_telegram_init_data(init_data: str, bot_token: str) -> dict[str, object]:
    if not init_data or not bot_token:
        raise TelegramInitDataError("Telegram init data или bot token отсутствуют.")

    pairs = parse.parse_qsl(init_data, keep_blank_values=True)
    payload = dict(pairs)
    received_hash = payload.pop("hash", None)
    if not received_hash:
        raise TelegramInitDataError("В init data отсутствует hash.")

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(payload.items(), key=lambda item: item[0])
    )
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        raise TelegramInitDataError("Подпись Telegram init data не прошла проверку.")

    auth_date_raw = payload.get("auth_date")
    if auth_date_raw:
        try:
            auth_date = int(str(auth_date_raw))
        except ValueError as exc:
            raise TelegramInitDataError("Некорректное auth_date в Telegram init data.") from exc
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if abs(now_ts - auth_date) > 86400:
            raise TelegramInitDataError("Telegram init data устарели.")

    return parse_telegram_user_without_validation(init_data)


def resolve_telegram_user(
    init_data: str,
    bot_token: str,
    *,
    allow_untrusted: bool = False,
) -> dict[str, object]:
    if bot_token:
        return validate_telegram_init_data(init_data, bot_token)
    if allow_untrusted:
        return parse_telegram_user_without_validation(init_data)
    raise TelegramInitDataError("Telegram Bot token не настроен.")


def send_telegram_message(bot_token: str, telegram_user_id: str, text: str) -> None:
    if not bot_token:
        raise TelegramInitDataError("Bot token не настроен.")

    payload = json.dumps(
        {
            "chat_id": telegram_user_id,
            "text": text,
        }
    ).encode("utf-8")
    req = request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as response:
        response.read()
