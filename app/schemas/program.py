from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_CUSTOM_EXERCISE_SLUGS = {
    "squat",
    "pushup",
    "plank",
    "lunge",
    "burpee",
    "band_row",
    "glute_bridge",
    "crunch",
    "calf_raise",
    "superman",
}


class ProgramCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    level: str
    duration_weeks: int
    is_custom: bool = False
    is_favorite: bool = False


class ProgramExerciseItemResponse(BaseModel):
    id: int
    order: int
    sets: int
    reps: int
    rest_sec: int
    tempo: str
    exercise_id: int
    exercise_name: str
    exercise_description: str
    equipment: str | None = None
    primary_muscles: str | None = None
    difficulty: str


class ProgramDetailResponse(BaseModel):
    id: int
    title: str
    description: str
    level: str
    duration_weeks: int
    is_favorite: bool = False
    exercises: list[ProgramExerciseItemResponse]


class WorkoutStartRequest(BaseModel):
    program_id: int = Field(gt=0)


class WorkoutStartResponse(BaseModel):
    session_id: int
    redirect_url: str


class WorkoutSessionShortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    program_id: int
    status: str


class WorkoutSetLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    exercise_id: int
    set_number: int
    reps_planned: int
    reps_done: int | None
    form_score_mock: int | None  # MOCK
    notes_mock: str | None  # MOCK


class ProgramLevelValidator(BaseModel):
    level: str

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"beginner", "intermediate", "advanced"}:
            raise ValueError("Уровень программы должен быть: beginner, intermediate или advanced.")
        return normalized


class ActiveProgramSummary(BaseModel):
    program_id: int
    title: str
    duration_weeks: int
    workouts_per_week: int
    completed_sessions: int
    total_sessions: int
    progress_percent: int


class ProgramSelectRequest(BaseModel):
    program_id: int = Field(gt=0)
    workouts_per_week: int = Field(ge=1, le=3)


class ProgramSelectResponse(BaseModel):
    message: str
    active_program: ActiveProgramSummary


class CustomProgramExerciseInput(BaseModel):
    exercise_slug: str
    sets: int = Field(ge=1, le=20)
    target_reps: int = Field(ge=1, le=300)
    rest_sec: int = Field(ge=10, le=600)

    @field_validator("exercise_slug")
    @classmethod
    def validate_exercise_slug(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_CUSTOM_EXERCISE_SLUGS:
            allowed = ", ".join(sorted(ALLOWED_CUSTOM_EXERCISE_SLUGS))
            raise ValueError(f"Допустимые упражнения: {allowed}.")
        return normalized


class CustomProgramSyncRequest(BaseModel):
    items: list[CustomProgramExerciseInput] = Field(default_factory=list, max_length=20)


class CustomProgramSyncResponse(BaseModel):
    message: str
    custom_program_id: int | None
    exercises_count: int
