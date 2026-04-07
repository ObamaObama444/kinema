from fastapi import Cookie, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_db
from app.core.security import TokenDecodeError, create_access_token, create_refresh_token, decode_token
from app.core.telegram import TelegramInitDataError, resolve_telegram_user
from app.crud.user import get_user_by_id, resolve_user_for_telegram_auth
from app.models.user import User


def _auth_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
    )


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure_cookie = settings.environment.lower() == "production"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=settings.refresh_token_expire_minutes * 60,
        path="/",
    )


def _resolve_user_from_telegram_init_data(
    telegram_init_data: str | None,
    db: Session,
) -> User | None:
    init_data = str(telegram_init_data or "").strip()
    if not init_data:
        return None

    allow_untrusted = (
        settings.environment.lower() != "production"
        and settings.allow_insecure_telegram_dev_auth
    )

    try:
        telegram_user = resolve_telegram_user(
            init_data,
            settings.telegram_bot_token,
            allow_untrusted=allow_untrusted,
        )
    except TelegramInitDataError:
        return None

    telegram_user_id = str(telegram_user.get("id") or "").strip()
    if not telegram_user_id:
        return None

    return resolve_user_for_telegram_auth(
        db,
        telegram_user_id=telegram_user_id,
        telegram_username=telegram_user.get("username"),
        telegram_first_name=telegram_user.get("first_name"),
        current_user=None,
    )


def _resolve_user_from_token(
    token: str | None,
    *,
    expected_type: str,
    db: Session,
) -> User | None:
    raw_token = str(token or "").strip()
    if not raw_token:
        return None

    try:
        payload = decode_token(raw_token)
    except TokenDecodeError:
        return None

    if payload.get("type") != expected_type:
        return None

    subject = payload.get("sub")
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        return None

    return get_user_by_id(db, user_id)


def _issue_session_for_user(response: Response | None, user: User) -> None:
    if response is None:
        return
    _set_auth_cookies(
        response,
        create_access_token(subject=str(user.id)),
        create_refresh_token(subject=str(user.id)),
    )


def get_current_user(
    response: Response,
    access_token: str | None = Cookie(default=None),
    refresh_token: str | None = Cookie(default=None),
    telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    db: Session = Depends(get_db),
) -> User:
    user = _resolve_user_from_token(access_token, expected_type="access", db=db)
    if user is not None:
        return user

    user = _resolve_user_from_token(refresh_token, expected_type="refresh", db=db)
    if user is not None:
        _issue_session_for_user(response, user)
        return user

    user = _resolve_user_from_telegram_init_data(telegram_init_data, db)
    if user is not None:
        _issue_session_for_user(response, user)
        return user

    raise _auth_error("Требуется авторизация.")
