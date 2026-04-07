from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    action_type: str | None = None
    action_label: str | None = None
    action_payload: str | None = None
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationItemResponse]
    unread_count: int


class NotificationCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    message: str = Field(min_length=1, max_length=500)


class MarkAllNotificationsReadResponse(BaseModel):
    updated: int


class MarkNotificationReadResponse(BaseModel):
    ok: bool
    unread_count: int


class ClearAllNotificationsResponse(BaseModel):
    deleted: int


class GenerateNotificationReportResponse(BaseModel):
    ok: bool
    report_markdown: str
    report_file_path: str
    avg_score: float | None = None
