from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.custom_exercises import router as custom_exercises_router
from app.api.exercises import router as exercises_router
from app.api.favorites import router as favorites_router
from app.api.goals import router as goals_router
from app.api.notifications import router as notifications_router
from app.api.onboarding import router as onboarding_router
from app.api.plan import router as plan_router
from app.api.profile import router as profile_router
from app.api.progress import router as progress_router
from app.api.records import router as records_router
from app.api.programs import router as programs_router
from app.api.reminders import router as reminders_router
from app.api.technique import router as technique_router
from app.api.telegram import router as telegram_router
from app.api.workouts import router as workouts_router
from app.core.assets import get_asset_version
from app.core.deps import get_db
from app.crud.onboarding import get_effective_user_onboarding
from app.models.user import User
from app.services.first_interview_snapshot import read_first_interview_snapshot
from app.services.personalized_plan import build_plan_signature
from app.services.personalized_plan_store import read_cached_personalized_plan, read_latest_cached_personalized_plan

router = APIRouter()
router.include_router(profile_router)
router.include_router(onboarding_router)
router.include_router(plan_router)
router.include_router(goals_router)
router.include_router(notifications_router)
router.include_router(programs_router)
router.include_router(exercises_router)
router.include_router(custom_exercises_router)
router.include_router(workouts_router)
router.include_router(technique_router)
router.include_router(favorites_router)
router.include_router(progress_router)
router.include_router(records_router)
router.include_router(reminders_router)
router.include_router(telegram_router)

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")
templates.env.globals["asset_version"] = get_asset_version


def _page_user_or_redirect(
    request: Request,
    db: Session = Depends(get_db),
) -> User | RedirectResponse:
    try:
        return get_current_user(
            response=Response(),
            access_token=request.cookies.get("access_token"),
            refresh_token=request.cookies.get("refresh_token"),
            db=db,
        )
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        raise


def _onboarding_redirect_if_needed(
    db: Session,
    user: User,
) -> RedirectResponse | None:
    onboarding = get_effective_user_onboarding(db, user.id)
    if onboarding is None or not onboarding.is_completed:
        return RedirectResponse(url="/app/onboarding", status_code=status.HTTP_302_FOUND)
    return None


def _render_mobile_page(
    request: Request,
    *,
    page_title: str,
    data_page: str,
    page_heading: str,
    page_scripts: list[str],
    data_view: str | None = None,
    page_subtitle: str | None = None,
    main_class: str | None = None,
    hide_header: bool = False,
    bootstrap_data: dict[str, object] | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        "app/mobile_page.html",
        {
            "request": request,
            "page_title": page_title,
            "data_page": data_page,
            "data_view": data_view,
            "page_heading": page_heading,
            "page_subtitle": page_subtitle,
            "page_scripts": page_scripts,
            "main_class": main_class,
            "hide_header": hide_header,
            "bootstrap_data": bootstrap_data,
        },
    )


def _authorized_mobile_page(
    request: Request,
    db: Session,
    current_user_or_redirect: User | RedirectResponse,
    *,
    page_title: str,
    data_page: str,
    page_heading: str,
    page_scripts: list[str],
    data_view: str | None = None,
    page_subtitle: str | None = None,
    main_class: str | None = None,
    hide_header: bool = False,
    bootstrap_data: dict[str, object] | None = None,
) -> Response:
    if isinstance(current_user_or_redirect, RedirectResponse):
        return current_user_or_redirect

    onboarding_redirect = _onboarding_redirect_if_needed(db, current_user_or_redirect)
    if onboarding_redirect is not None:
        return onboarding_redirect

    return _render_mobile_page(
        request,
        page_title=page_title,
        data_page=data_page,
        page_heading=page_heading,
        page_scripts=page_scripts,
        data_view=data_view,
        page_subtitle=page_subtitle,
        main_class=main_class,
        hide_header=hide_header,
        bootstrap_data=bootstrap_data,
    )


def _bootstrap_public_user(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "telegram_linked": bool(user.telegram_user_id),
        "telegram_user_id": user.telegram_user_id,
        "telegram_username": user.telegram_username,
        "telegram_first_name": user.telegram_first_name,
    }


def _bootstrap_personalized_plan(user: User) -> dict[str, object] | None:
    snapshot = read_first_interview_snapshot(user.id)
    signature = build_plan_signature(snapshot["data"], snapshot=snapshot) if snapshot else None
    plan = read_cached_personalized_plan(user.id, signature) if signature else None
    if plan is None:
        plan = read_latest_cached_personalized_plan(user.id)
    if plan is None:
        return None
    return plan.model_dump(mode="json")


@router.get("/", response_class=HTMLResponse)
def landing_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "page_title": "Kinematics",
            "headline": "Kinematics",
            "subheadline": "Персональный ИИ-тренер для самостоятельных тренировок",
        },
    )


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@router.get("/app", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Записи | Kinematics",
        data_page="progress",
        data_view="records-hub",
        page_heading="Записи",
        page_subtitle="Ежедневные цели по воде и шагам, пульс и давление.",
        page_scripts=["/assets/js/records-page.js"],
        hide_header=True,
    )


@router.get("/app/profile", response_class=HTMLResponse)
def profile_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Я | Kinematics",
        data_page="me",
        data_view="profile-hub",
        page_heading="Я",
        page_subtitle="Профиль, избранное, настройки, календарь и вес.",
        page_scripts=["/assets/js/profile-page.js"],
        hide_header=True,
    )


@router.get("/app/profile/edit", response_class=HTMLResponse)
def profile_edit_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Профиль | Kinematics",
        data_page="me",
        data_view="profile-edit",
        page_heading="Профиль",
        page_subtitle="Никнейм, аватар и базовые параметры.",
        page_scripts=["/assets/js/profile-edit-page.js"],
    )


@router.get("/app/profile/favorites", response_class=HTMLResponse)
def profile_favorites_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Избранное | Kinematics",
        data_page="me",
        data_view="profile-favorites",
        page_heading="Избранное",
        page_subtitle="Сохранённые тренировки и упражнения.",
        page_scripts=["/assets/js/favorites-page.js"],
        hide_header=True,
    )


@router.get("/app/profile/reminders", response_class=HTMLResponse)
def profile_reminders_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Напоминания | Kinematics",
        data_page="me",
        data_view="profile-reminders",
        page_heading="Напоминания",
        page_subtitle="Тренировки, вода и собственные Telegram-уведомления.",
        page_scripts=["/assets/js/reminders-page.js"],
    )


@router.get("/app/profile/settings", response_class=HTMLResponse)
def profile_settings_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Настройки | Kinematics",
        data_page="me",
        data_view="profile-settings",
        page_heading="Настройки",
        page_subtitle="Профиль, избранное, напоминания и общие параметры.",
        page_scripts=["/assets/js/settings-page.js"],
        hide_header=True,
    )


@router.get("/app/profile/settings/general", response_class=HTMLResponse)
def profile_general_settings_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Общие настройки | Kinematics",
        data_page="me",
        data_view="profile-settings-general",
        page_heading="Общие настройки",
        page_subtitle="Тема, язык, единицы измерения и Telegram link.",
        page_scripts=["/assets/js/settings-general-page.js"],
        hide_header=True,
    )


@router.get("/app/profile/settings/disclaimer", response_class=HTMLResponse)
def profile_settings_disclaimer_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Отказ от ответственности | Kinematics",
        data_page="me",
        data_view="profile-settings-disclaimer",
        page_heading="Отказ от ответственности",
        page_subtitle="Важная информация об использовании рекомендаций.",
        page_scripts=["/assets/js/settings-disclaimer-page.js"],
        hide_header=True,
    )


@router.get("/app/profile/weight", response_class=HTMLResponse)
def profile_weight_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Вес | Kinematics",
        data_page="me",
        data_view="profile-weight",
        page_heading="Вес",
        page_subtitle="История веса, обновления раз в 5 часов и ИМТ.",
        page_scripts=["/assets/js/weight-page.js"],
    )


@router.get("/app/goals")
def goals_section_redirect() -> RedirectResponse:
    return RedirectResponse(url="/app/profile", status_code=status.HTTP_302_FOUND)


@router.get("/app/onboarding", response_class=HTMLResponse)
def onboarding_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    if isinstance(current_user_or_redirect, RedirectResponse):
        return current_user_or_redirect
    return templates.TemplateResponse(
        "app/onboarding.html",
        {
            "request": request,
            "page_title": "Onboarding | Kinematics",
        },
    )


@router.get("/app/programs", response_class=HTMLResponse)
def programs_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    bootstrap_data = None
    if isinstance(current_user_or_redirect, User):
        bootstrap_data = {
            "profile": _bootstrap_public_user(current_user_or_redirect),
            "plan": _bootstrap_personalized_plan(current_user_or_redirect),
        }
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Мой план | Kinematics",
        data_page="plan",
        page_heading="Мой план",
        page_subtitle="Персональный 10-дневный маршрут, собранный Mistral по первому интервью.",
        page_scripts=["/assets/js/programs-page.js"],
        bootstrap_data=bootstrap_data,
    )


@router.get("/app/programs/{program_id}", response_class=HTMLResponse)
def program_detail_page(
    program_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    _ = program_id
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Детали плана | Kinematics",
        data_page="plan",
        page_heading="Детали плана",
        page_subtitle="Состав программы, упражнения и быстрый старт тренировки.",
        page_scripts=["/assets/js/program-detail-page.js"],
    )


@router.get("/app/theme")
def theme_page() -> RedirectResponse:
    return RedirectResponse(url="/app/profile/settings/general", status_code=status.HTTP_302_FOUND)


@router.get("/app/catalog", response_class=HTMLResponse)
def exercise_catalog_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Упражнения | Kinematics",
        data_page="workouts",
        data_view="exercise-hub",
        page_heading="Упражнения",
        page_subtitle="Список упражнений из старого каталога и заготовка под текущий план.",
        page_scripts=["/assets/js/catalog-page.js"],
        hide_header=True,
    )


@router.get("/app/catalog/new", response_class=HTMLResponse)
def exercise_create_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Добавить упражнение | Kinematics",
        data_page="workouts",
        data_view="exercise-create",
        page_heading="Добавить упражнение",
        page_subtitle="Эталонный ролик одного повтора и базовые параметры нового упражнения.",
        page_scripts=[
            "/assets/js/custom-technique-utils.js",
            "/assets/js/exercise-create-page.js",
        ],
        hide_header=True,
    )


@router.get("/app/catalog/custom/{profile_id}", response_class=HTMLResponse)
def exercise_calibration_page(
    profile_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    _ = profile_id
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Калибровка упражнения | Kinematics",
        data_page="workouts",
        data_view="exercise-calibration",
        page_heading="Калибровка упражнения",
        page_subtitle="Эталонная модель, допуски, тест с камерой и публикация.",
        page_scripts=[
            "/assets/js/custom-technique-utils.js",
            "/assets/js/exercise-calibration-page.js",
        ],
        hide_header=True,
    )


@router.get("/app/technique/{session_id}", response_class=HTMLResponse)
def technique_session_page(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    _ = session_id
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Проверка техники | Kinematics",
        data_page="workouts",
        data_view="technique-session",
        page_heading="Проверка техники",
        page_subtitle="Камера, live-подсказки и real-time оценка повторов.",
        page_scripts=["/assets/js/technique-runtime.js", "/assets/js/technique-session-page.js"],
        hide_header=True,
    )


@router.get("/app/workout/{session_id}", response_class=HTMLResponse)
def workout_page(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user_or_redirect: User | RedirectResponse = Depends(_page_user_or_redirect),
) -> Response:
    _ = session_id
    return _authorized_mobile_page(
        request,
        db,
        current_user_or_redirect,
        page_title="Workout Flow | Kinematics",
        data_page="workouts",
        page_heading="Workout Flow",
        page_subtitle="Активная сессия, таймер и поток упражнения.",
        page_scripts=["/assets/js/workout-page.js", "/assets/js/workout.js"],
    )


@router.get("/profile")
def profile_shortcut() -> RedirectResponse:
    return RedirectResponse(url="/app/profile", status_code=status.HTTP_302_FOUND)


@router.get("/goals")
def goals_shortcut() -> RedirectResponse:
    return RedirectResponse(url="/app/profile", status_code=status.HTTP_302_FOUND)


@router.get("/app/exercises")
def exercises_legacy_shortcut() -> RedirectResponse:
    return RedirectResponse(url="/app/catalog", status_code=status.HTTP_302_FOUND)
