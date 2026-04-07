from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.progress import resolve_timezone_name
from app.core.telegram import send_telegram_message
from app.models.reminder import ReminderRule
from app.models.user import User

logger = logging.getLogger(__name__)

_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _parse_days(rule: ReminderRule) -> list[str]:
    if not rule.days_json:
        return []
    try:
        parsed = json.loads(rule.days_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip().lower() for item in parsed if str(item).strip().lower() in _WEEKDAYS]


def _last_sent_local(rule: ReminderRule, tz: ZoneInfo) -> datetime | None:
    if rule.last_sent_at is None:
        return None
    source = rule.last_sent_at
    if source.tzinfo is None:
        source = source.replace(tzinfo=timezone.utc)
    return source.astimezone(tz)


def _is_rule_due(rule: ReminderRule, now_utc: datetime) -> bool:
    timezone_name = resolve_timezone_name(rule.timezone)
    tz = ZoneInfo(timezone_name)
    now_local = now_utc.astimezone(tz)
    try:
        hours_raw, minutes_raw = str(rule.time_local).split(":", 1)
        hours = int(hours_raw)
        minutes = int(minutes_raw)
    except (ValueError, AttributeError):
        return False

    if now_local.hour != hours or now_local.minute != minutes:
        return False

    days = _parse_days(rule)
    if days and _WEEKDAYS[now_local.weekday()] not in days:
        return False

    last_sent_local = _last_sent_local(rule, tz)
    if last_sent_local is not None:
        if (
            last_sent_local.date() == now_local.date()
            and last_sent_local.hour == hours
            and last_sent_local.minute == minutes
        ):
            return False

    return True


class ReminderScheduler:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if not settings.reminder_scheduler_enabled or not settings.telegram_bot_token:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name="reminder-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None

    def _loop(self) -> None:
        interval = max(10, int(settings.reminder_scheduler_interval_sec))
        while not self._stop_event.wait(interval):
            try:
                self.run_once()
            except Exception:  # pragma: no cover
                logger.exception("Reminder scheduler iteration failed")

    def run_once(self) -> None:
        if not settings.telegram_bot_token:
            return
        now_utc = datetime.now(timezone.utc)
        with SessionLocal() as db:
            rows = db.execute(
                select(ReminderRule, User)
                .join(User, User.id == ReminderRule.user_id)
                .where(ReminderRule.enabled.is_(True), User.telegram_user_id.is_not(None))
            ).all()

            dirty = False
            for rule, user in rows:
                if not user.telegram_user_id or not _is_rule_due(rule, now_utc):
                    continue
                try:
                    send_telegram_message(settings.telegram_bot_token, str(user.telegram_user_id), rule.message)
                except Exception:  # pragma: no cover
                    logger.exception("Failed to send Telegram reminder %s to user %s", rule.id, user.id)
                    continue
                rule.last_sent_at = now_utc
                db.add(rule)
                dirty = True

            if dirty:
                db.commit()


reminder_scheduler = ReminderScheduler()
