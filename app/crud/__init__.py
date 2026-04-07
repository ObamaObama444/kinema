from app.crud.favorite import add_favorite, get_favorite, list_favorites_by_type, remove_favorite
from app.crud.goal import (
    GoalAlreadyExistsError,
    create_goal,
    delete_goal_by_user_id,
    get_goal_by_user_id,
    get_goals_by_user_id,
)
from app.crud.notification import (
    count_unread_notifications,
    create_notification,
    create_notification_safe,
    delete_all_notifications,
    get_notification_by_id,
    list_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)
from app.crud.profile import (
    get_active_program_snapshot,
    get_or_create_profile,
    get_profile_by_user_id,
    set_active_program,
    upsert_profile,
)
from app.crud.reminder import delete_reminder, get_reminder_by_id, list_user_reminders
from app.crud.settings import get_or_create_user_settings, get_user_settings
from app.crud.program import ensure_seed_programs, get_program_by_id, get_program_with_exercises, list_programs
from app.crud.user import create_user, get_user_by_email, get_user_by_id, update_user_avatar, update_user_name, update_user_telegram_link
from app.crud.weight import get_weight_entry_for_day, list_weight_entries
from app.crud.workout import create_workout_session, get_workout_session_by_id

__all__ = [
    "add_favorite",
    "get_favorite",
    "remove_favorite",
    "list_favorites_by_type",
    "create_user",
    "get_user_by_email",
    "get_user_by_id",
    "update_user_name",
    "update_user_avatar",
    "update_user_telegram_link",
    "get_profile_by_user_id",
    "get_or_create_profile",
    "upsert_profile",
    "set_active_program",
    "get_active_program_snapshot",
    "get_user_settings",
    "get_or_create_user_settings",
    "get_goal_by_user_id",
    "get_goals_by_user_id",
    "create_goal",
    "delete_goal_by_user_id",
    "GoalAlreadyExistsError",
    "list_notifications",
    "count_unread_notifications",
    "create_notification",
    "create_notification_safe",
    "get_notification_by_id",
    "delete_all_notifications",
    "mark_all_notifications_as_read",
    "mark_notification_as_read",
    "ensure_seed_programs",
    "list_programs",
    "get_program_by_id",
    "get_program_with_exercises",
    "list_weight_entries",
    "get_weight_entry_for_day",
    "list_user_reminders",
    "get_reminder_by_id",
    "delete_reminder",
    "create_workout_session",
    "get_workout_session_by_id",
]
