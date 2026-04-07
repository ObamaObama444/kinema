from pydantic import BaseModel, Field


class TelegramLinkRequest(BaseModel):
    init_data: str = Field(min_length=1)


class TelegramLinkResponse(BaseModel):
    ok: bool
    telegram_user_id: str
    telegram_username: str | None = None
    telegram_first_name: str | None = None
