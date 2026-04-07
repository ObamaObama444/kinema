from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.deps import get_db
from app.core.telegram import TelegramInitDataError, resolve_telegram_user
from app.crud.user import TelegramLinkConflictError, link_telegram_account as link_telegram_account_for_user
from app.models.user import User
from app.schemas.telegram import TelegramLinkRequest, TelegramLinkResponse

router = APIRouter(tags=["telegram"])


@router.post("/api/telegram/link", response_model=TelegramLinkResponse)
def link_telegram_account_route(
    payload: TelegramLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TelegramLinkResponse:
    allow_untrusted = (
        settings.environment.lower() != "production"
        and settings.allow_insecure_telegram_dev_auth
    )

    try:
        telegram_user = resolve_telegram_user(
            payload.init_data,
            settings.telegram_bot_token,
            allow_untrusted=allow_untrusted,
        )
    except TelegramInitDataError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    telegram_user_id = str(telegram_user.get("id") or "").strip()
    if not telegram_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram user id не найден.")

    try:
        user = link_telegram_account_for_user(
            db,
            current_user,
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_user.get("username"),
            telegram_first_name=telegram_user.get("first_name"),
        )
    except TelegramLinkConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось привязать Telegram-аккаунт.",
        ) from exc

    return TelegramLinkResponse(
        ok=True,
        telegram_user_id=str(user.telegram_user_id),
        telegram_username=user.telegram_username,
        telegram_first_name=user.telegram_first_name,
    )
