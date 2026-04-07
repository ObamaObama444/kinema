import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.deps import get_db
from app.crud.notification import (
    count_unread_notifications,
    create_notification,
    delete_all_notifications,
    get_notification_by_id,
    list_all_notifications,
    list_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)
from app.models.user import User
from app.schemas.notification import (
    ClearAllNotificationsResponse,
    GenerateNotificationReportResponse,
    MarkAllNotificationsReadResponse,
    MarkNotificationReadResponse,
    NotificationCreateRequest,
    NotificationItemResponse,
    NotificationListResponse,
)
from app.services.training_report import (
    LOGS_DIR,
    REPORTS_DIR_RESOLVED,
    ReportDependencyError,
    ReportGenerationError,
    generate_training_report_from_log,
)

router = APIRouter(tags=["notifications"])

ACTION_GENERATE_TRAINING_REPORT = "generate_training_report"
REPORT_CACHE_VERSION = "4"


def _parse_action_payload(payload_text: str | None) -> dict[str, str]:
    if not payload_text:
        return {}

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return {}

    if not isinstance(payload, dict):
        return {}

    return {str(key): str(value) for key, value in payload.items()}


def _parse_avg_score(payload: dict[str, str]) -> float | None:
    raw_score = payload.get("avg_score")
    if raw_score is None:
        return None

    try:
        return float(raw_score)
    except (TypeError, ValueError):
        return None


def _resolve_safe_report_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None

    candidate = Path(path_value).expanduser().resolve()
    try:
        candidate.relative_to(REPORTS_DIR_RESOLVED)
    except ValueError:
        return None
    return candidate


@router.get("/api/notifications", response_model=NotificationListResponse)
def get_notifications(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    try:
        notifications = list_notifications(db, current_user.id, limit=limit)
        unread_count = count_unread_notifications(db, current_user.id)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось загрузить уведомления.",
        ) from exc

    return NotificationListResponse(
        items=[NotificationItemResponse.model_validate(item) for item in notifications],
        unread_count=unread_count,
    )


@router.post("/api/notifications", response_model=NotificationItemResponse, status_code=status.HTTP_201_CREATED)
def create_user_notification(
    payload: NotificationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationItemResponse:
    try:
        notification = create_notification(
            db,
            user_id=current_user.id,
            title=payload.title,
            message=payload.message,
        )
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось создать уведомление.",
        ) from exc

    return NotificationItemResponse.model_validate(notification)


@router.post("/api/notifications/read-all", response_model=MarkAllNotificationsReadResponse)
def read_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkAllNotificationsReadResponse:
    try:
        updated = mark_all_notifications_as_read(db, current_user.id)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось отметить уведомления как прочитанные.",
        ) from exc

    return MarkAllNotificationsReadResponse(updated=updated)


@router.post("/api/notifications/clear-all", response_model=ClearAllNotificationsResponse)
def clear_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClearAllNotificationsResponse:
    try:
        notifications = list_all_notifications(db, current_user.id)
        for item in notifications:
            if item.action_type != ACTION_GENERATE_TRAINING_REPORT:
                continue

            payload = _parse_action_payload(item.action_payload)
            safe_report_path = _resolve_safe_report_path(payload.get("report_path"))
            if safe_report_path is None:
                continue
            if not safe_report_path.exists() or not safe_report_path.is_file():
                continue

            try:
                safe_report_path.unlink()
            except OSError:
                continue

        deleted = delete_all_notifications(db, current_user.id)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось очистить уведомления.",
        ) from exc

    return ClearAllNotificationsResponse(deleted=deleted)


@router.post("/api/notifications/{notification_id}/read", response_model=MarkNotificationReadResponse)
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkNotificationReadResponse:
    try:
        changed = mark_notification_as_read(db, current_user.id, notification_id)
        unread_count = count_unread_notifications(db, current_user.id)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить уведомление.",
        ) from exc

    if not changed:
        return MarkNotificationReadResponse(ok=False, unread_count=unread_count)

    return MarkNotificationReadResponse(ok=True, unread_count=unread_count)


@router.post(
    "/api/notifications/{notification_id}/generate-report",
    response_model=GenerateNotificationReportResponse,
)
def generate_report_for_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateNotificationReportResponse:
    notification = get_notification_by_id(db, user_id=current_user.id, notification_id=notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Уведомление не найдено.",
        )

    if notification.action_type != ACTION_GENERATE_TRAINING_REPORT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для этого уведомления отчёт недоступен.",
        )

    payload = _parse_action_payload(notification.action_payload)
    log_path_value = payload.get("log_path")
    if not log_path_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="В уведомлении отсутствует путь к JSON-логу.",
        )

    cached_report_path = _resolve_safe_report_path(payload.get("report_path"))
    use_cached_report = (
        payload.get("report_version") == REPORT_CACHE_VERSION
        and cached_report_path is not None
        and cached_report_path.exists()
        and cached_report_path.is_file()
    )
    if use_cached_report:
        try:
            cached_text = cached_report_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось прочитать ранее созданный отчёт.",
            ) from exc

        payload["generated"] = "true"
        notification.action_payload = json.dumps(payload, ensure_ascii=False)
        notification.is_read = True
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()

        return GenerateNotificationReportResponse(
            ok=True,
            report_markdown=cached_text or "нет данных",
            report_file_path=str(cached_report_path),
            avg_score=_parse_avg_score(payload),
        )

    log_path = Path(log_path_value).expanduser().resolve()
    try:
        log_path.relative_to(LOGS_DIR)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Путь к логу некорректен.",
        ) from exc

    try:
        result = generate_training_report_from_log(log_path=log_path, user_id=current_user.id)
    except ReportDependencyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "LLM-модуль отчётов не готов: "
                f"{exc}. Установите зависимости llama-cpp-python и huggingface_hub."
            ),
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="JSON-лог для генерации отчёта не найден.",
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Этот JSON-лог принадлежит другому пользователю.",
        ) from exc
    except ReportGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось сгенерировать отчёт: {exc}",
        ) from exc

    payload["report_path"] = str(result.report_path)
    payload["generated"] = "true"
    payload["report_version"] = REPORT_CACHE_VERSION
    if result.avg_score is not None:
        payload["avg_score"] = f"{result.avg_score:.2f}"

    try:
        notification.action_payload = json.dumps(payload, ensure_ascii=False)
        notification.is_read = True
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Отчёт сгенерирован, но не удалось обновить уведомление.",
        ) from exc

    return GenerateNotificationReportResponse(
        ok=True,
        report_markdown=result.report_markdown,
        report_file_path=str(result.report_path),
        avg_score=result.avg_score,
    )
