from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api.onboarding import PLAN_GENERATION_UNAVAILABLE_CODE, complete_onboarding


def build_onboarding_record() -> SimpleNamespace:
    return SimpleNamespace(
        main_goal="lose_weight",
        motivation="feel_better",
        desired_outcome="more_energy",
        focus_area="legs",
        gender="male",
        current_body_shape="round",
        target_body_shape="lean",
        age=31,
        height_cm=182,
        current_weight_kg=94.0,
        target_weight_kg=84.0,
        fitness_level="beginner",
        activity_level="sedentary",
        goal_pace="moderate",
        training_frequency=3,
        calorie_tracking="no",
        diet_type="balanced",
        self_image="neutral",
        reminders_enabled=False,
        reminder_time_local=None,
        onboarding_version="v1",
        interest_tags="[]",
        equipment_tags='["none"]',
        injury_areas='["none"]',
        training_days='["mon","wed","fri"]',
        is_completed=False,
        completed_at=None,
    )


class OnboardingCompleteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.current_user = SimpleNamespace(id=4, telegram_user_id=None)
        self.db = SimpleNamespace(commit=lambda: None, refresh=lambda _record: None, rollback=lambda: None)
        self.profile = SimpleNamespace(height_cm=None, weight_kg=None, age=None, level=None)
        self.snapshot = {
            "snapshot_version": "v1",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "data": {
                "main_goal": "lose_weight",
                "focus_area": "legs",
                "training_frequency": 3,
            },
        }

    @patch("app.api.onboarding._state_response")
    @patch("app.api.onboarding.schedule_personalized_plan_generation")
    @patch("app.api.onboarding.generate_and_cache_personalized_plan")
    @patch("app.api.onboarding.ensure_first_interview_snapshot")
    @patch("app.api.onboarding._upsert_goal")
    @patch("app.api.onboarding.build_goal_target_value")
    @patch("app.api.onboarding.build_onboarding_derived")
    @patch("app.api.onboarding.get_or_create_profile")
    @patch("app.api.onboarding.get_or_create_user_onboarding")
    @patch("app.api.onboarding.get_user_onboarding")
    @patch("app.api.onboarding.validate_onboarding_data")
    def test_complete_onboarding_generates_plan_before_success(
        self,
        validate_data,
        get_user_onboarding,
        get_or_create_user_onboarding,
        get_or_create_profile,
        build_onboarding_derived,
        build_goal_target_value,
        _upsert_goal,
        ensure_snapshot,
        generate_and_cache,
        schedule_generation,
        state_response,
    ) -> None:
        record = build_onboarding_record()
        get_user_onboarding.return_value = record
        get_or_create_user_onboarding.return_value = record
        get_or_create_profile.return_value = self.profile
        build_onboarding_derived.return_value = {"goal_target_value": "84"}
        build_goal_target_value.return_value = "84"
        ensure_snapshot.return_value = self.snapshot
        generate_and_cache.return_value = ("test-signature", object())
        state_response.return_value = SimpleNamespace(
            model_dump=lambda: {
                "status": "completed",
                "is_completed": True,
                "resume_step": "done",
                "data": {},
                "derived": {},
            }
        )

        result = complete_onboarding(db=self.db, current_user=self.current_user)

        self.assertTrue(result.plan_ready)
        generate_and_cache.assert_called_once_with(self.current_user.id, self.snapshot)
        schedule_generation.assert_not_called()
        validate_data.assert_called()

    @patch("app.api.onboarding._state_response")
    @patch("app.api.onboarding.schedule_personalized_plan_generation")
    @patch("app.api.onboarding.generate_and_cache_personalized_plan")
    @patch("app.api.onboarding.ensure_first_interview_snapshot")
    @patch("app.api.onboarding._upsert_goal")
    @patch("app.api.onboarding.build_goal_target_value")
    @patch("app.api.onboarding.build_onboarding_derived")
    @patch("app.api.onboarding.get_or_create_profile")
    @patch("app.api.onboarding.get_or_create_user_onboarding")
    @patch("app.api.onboarding.get_user_onboarding")
    @patch("app.api.onboarding.validate_onboarding_data")
    def test_complete_onboarding_returns_503_when_plan_is_not_ready(
        self,
        validate_data,
        get_user_onboarding,
        get_or_create_user_onboarding,
        get_or_create_profile,
        build_onboarding_derived,
        build_goal_target_value,
        _upsert_goal,
        ensure_snapshot,
        generate_and_cache,
        schedule_generation,
        state_response,
    ) -> None:
        record = build_onboarding_record()
        get_user_onboarding.return_value = record
        get_or_create_user_onboarding.return_value = record
        get_or_create_profile.return_value = self.profile
        build_onboarding_derived.return_value = {"goal_target_value": "84"}
        build_goal_target_value.return_value = "84"
        ensure_snapshot.return_value = self.snapshot
        generate_and_cache.return_value = ("test-signature", None)
        state_response.return_value = SimpleNamespace(model_dump=lambda: {})

        with self.assertRaises(HTTPException) as exc:
            complete_onboarding(db=self.db, current_user=self.current_user)

        self.assertEqual(exc.exception.status_code, 503)
        self.assertEqual(exc.exception.detail["code"], PLAN_GENERATION_UNAVAILABLE_CODE)
        schedule_generation.assert_called_once_with(self.current_user.id, self.snapshot, force=True)
        validate_data.assert_called()


if __name__ == "__main__":
    unittest.main()
