from app.schemas.auth import LoginRequest, RegisterRequest, UserPublic
from app.schemas.exercise import ExerciseCatalogItemResponse
from app.schemas.favorite import (
    FavoriteExerciseItemResponse,
    FavoriteMutationResponse,
    FavoriteProgramItemResponse,
    FavoritesResponse,
)
from app.schemas.goal import GoalCreateRequest, GoalResponse
from app.schemas.notification import (
    ClearAllNotificationsResponse,
    GenerateNotificationReportResponse,
    MarkAllNotificationsReadResponse,
    MarkNotificationReadResponse,
    NotificationCreateRequest,
    NotificationItemResponse,
    NotificationListResponse,
)
from app.schemas.onboarding import (
    OnboardingCompleteResponse,
    OnboardingDataResponse,
    OnboardingDerivedResponse,
    OnboardingPatchRequest,
    OnboardingResetResponse,
    OnboardingStateResponse,
)
from app.schemas.progress import (
    ProgressCalendarDayResponse,
    ProgressSummaryResponse,
    ProgressWeightPointResponse,
)
from app.schemas.profile import AccountResponse, AccountUpdateRequest, ProfileResponse, ProfileUpdateRequest
from app.schemas.program import (
    ActiveProgramSummary,
    CustomProgramExerciseInput,
    CustomProgramSyncRequest,
    CustomProgramSyncResponse,
    ProgramCardResponse,
    ProgramDetailResponse,
    ProgramExerciseItemResponse,
    ProgramSelectRequest,
    ProgramSelectResponse,
    WorkoutSessionShortResponse,
    WorkoutSetLogResponse,
    WorkoutStartRequest,
    WorkoutStartResponse,
)
from app.schemas.reminder import (
    ReminderRuleCreateRequest,
    ReminderRuleListResponse,
    ReminderRulePatchRequest,
    ReminderRuleResponse,
)
from app.schemas.settings import UserSettingsPatchRequest, UserSettingsResponse
from app.schemas.telegram import TelegramLinkRequest, TelegramLinkResponse
from app.schemas.weight import WeightEntryCreateRequest, WeightEntryResponse, WeightHistorySummaryResponse

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "UserPublic",
    "ExerciseCatalogItemResponse",
    "FavoriteProgramItemResponse",
    "FavoriteExerciseItemResponse",
    "FavoritesResponse",
    "FavoriteMutationResponse",
    "ProfileUpdateRequest",
    "ProfileResponse",
    "AccountUpdateRequest",
    "AccountResponse",
    "GoalCreateRequest",
    "GoalResponse",
    "ProgramCardResponse",
    "ProgramExerciseItemResponse",
    "ProgramDetailResponse",
    "WorkoutStartRequest",
    "WorkoutStartResponse",
    "WorkoutSessionShortResponse",
    "WorkoutSetLogResponse",
    "ActiveProgramSummary",
    "ProgramSelectRequest",
    "ProgramSelectResponse",
    "CustomProgramExerciseInput",
    "CustomProgramSyncRequest",
    "CustomProgramSyncResponse",
    "NotificationItemResponse",
    "NotificationListResponse",
    "NotificationCreateRequest",
    "OnboardingPatchRequest",
    "OnboardingDataResponse",
    "OnboardingDerivedResponse",
    "OnboardingStateResponse",
    "OnboardingCompleteResponse",
    "OnboardingResetResponse",
    "UserSettingsPatchRequest",
    "UserSettingsResponse",
    "WeightEntryCreateRequest",
    "WeightEntryResponse",
    "WeightHistorySummaryResponse",
    "ReminderRuleCreateRequest",
    "ReminderRulePatchRequest",
    "ReminderRuleResponse",
    "ReminderRuleListResponse",
    "TelegramLinkRequest",
    "TelegramLinkResponse",
    "ProgressCalendarDayResponse",
    "ProgressWeightPointResponse",
    "ProgressSummaryResponse",
    "ClearAllNotificationsResponse",
    "MarkAllNotificationsReadResponse",
    "MarkNotificationReadResponse",
    "GenerateNotificationReportResponse",
]
