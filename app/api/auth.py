from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.assets import get_asset_version
from app.core.config import settings
from app.core.deps import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.core.telegram import TelegramInitDataError, resolve_telegram_user
from app.crud.user import (
    TelegramLinkConflictError,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_public_user_email,
    resolve_user_for_telegram_auth,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TelegramAuthRequest, UserPublic

router = APIRouter(tags=["auth"])

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")
templates.env.globals["asset_version"] = get_asset_version


def _set_auth_cookies(response: JSONResponse, access_token: str, refresh_token: str) -> None:
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


def _get_current_user_if_any(request: Request, db: Session) -> User | None:
    for cookie_name, expected_type in (("access_token", "access"), ("refresh_token", "refresh")):
        token = request.cookies.get(cookie_name)
        if not token:
            continue

        try:
            payload = decode_token(token)
        except Exception:
            continue

        if payload.get("type") != expected_type:
            continue

        subject = payload.get("sub")
        try:
            user_id = int(subject)
        except (TypeError, ValueError):
            continue

        user = get_user_by_id(db, user_id)
        if user is not None:
            return user

    return None


def _build_user_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=get_public_user_email(user),
        name=user.name,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )


@router.post("/api/auth/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserPublic:
    existing_user = get_user_by_email(db, payload.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует.",
        )

    try:
        user = create_user(
            db=db,
            email=payload.email,
            password=payload.password,
            name=payload.name,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует.",
        ) from exc

    return _build_user_public(user)


@router.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> JSONResponse:
    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль.",
        )

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    response = JSONResponse(
        {
            "message": "Вход выполнен успешно.",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    )
    _set_auth_cookies(response, access_token, refresh_token)

    return response


@router.post("/api/auth/telegram", response_model=UserPublic)
def telegram_login(
    payload: TelegramAuthRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    telegram_user_id = str(telegram_user.get("id") or "").strip()
    if not telegram_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram user id не найден.",
        )

    try:
        user = resolve_user_for_telegram_auth(
            db,
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_user.get("username"),
            telegram_first_name=telegram_user.get("first_name"),
            current_user=_get_current_user_if_any(request, db),
        )
    except TelegramLinkConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    response = JSONResponse(_build_user_public(user).model_dump(mode="json"))
    _set_auth_cookies(response, access_token, refresh_token)
    return response


@router.post("/api/auth/logout")
def logout() -> JSONResponse:
    response = JSONResponse({"message": "Вы вышли из аккаунта."})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response


@router.get("/api/auth/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return _build_user_public(current_user)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "page_title": "Вход | Kinematics",
        },
    )


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "auth/register.html",
        {
            "request": request,
            "page_title": "Регистрация | Kinematics",
        },
    )
