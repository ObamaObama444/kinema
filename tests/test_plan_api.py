from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api.plan import PLAN_GENERATION_UNAVAILABLE_CODE, get_personalized_plan
from app.schemas.plan import PersonalizedPlanResponse


def build_plan(source: str = "mistral") -> PersonalizedPlanResponse:
    days = []
    for day_number in range(1, 11):
        days.append(
            {
                "day_number": day_number,
                "stage_number": 1,
                "date_label": f"{day_number:02d}.03 · пн",
                "title": f"День {day_number}",
                "subtitle": "Короткая тренировка",
                "duration_min": 12,
                "estimated_kcal": 86,
                "intensity": "Рабочий темп",
                "emphasis": "Фокус на ноги",
                "note": "Держим ровный темп и технику.",
                "kind": "workout",
                "exercises": [
                    {
                        "slug": "squat",
                        "title": "Приседания",
                        "details": "Контроль корпуса",
                        "sets": 3,
                        "reps": 12,
                        "rest_sec": 30,
                    }
                ],
                "is_highlighted": day_number == 1,
            }
        )

    return PersonalizedPlanResponse.model_validate(
        {
            "signature": "test-signature",
            "source": source,
            "generated_at": datetime.now(timezone.utc),
            "headline": "Ноги",
            "subheadline": "Сжигаем жир",
            "tags": ["Похудение", "Ноги"],
            "summary_items": [
                {"label": "Сложность Плана", "value": "Новичок"},
                {"label": "Цель", "value": "Сбросить Вес"},
            ],
            "stages": [
                {
                    "stage_number": 1,
                    "title": "Этап 1",
                    "subtitle": "Рабочий блок",
                    "badge": "Этап 1",
                    "days": days,
                }
            ],
        }
    )


class PlanApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.current_user = SimpleNamespace(id=4)
        self.snapshot = {
            "snapshot_version": "v1",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "data": {"main_goal": "lose_weight", "focus_area": "legs"},
        }

    @patch("app.api.plan.read_cached_personalized_plan")
    @patch("app.api.plan.build_plan_signature")
    @patch("app.api.plan.read_first_interview_snapshot")
    @patch("app.api.plan.generate_and_cache_personalized_plan")
    def test_returns_cached_plan_without_regeneration(self, generate_and_cache, read_snapshot, build_signature, read_cached) -> None:
        cached_plan = build_plan()
        read_snapshot.return_value = self.snapshot
        build_signature.return_value = "test-signature"
        read_cached.return_value = cached_plan

        result = get_personalized_plan(refresh=False, db=object(), current_user=self.current_user)

        self.assertEqual(result.signature, cached_plan.signature)
        generate_and_cache.assert_not_called()

    @patch("app.api.plan.generate_and_cache_personalized_plan")
    @patch("app.api.plan.schedule_personalized_plan_generation")
    @patch("app.api.plan.read_cached_personalized_plan")
    @patch("app.api.plan.build_plan_signature")
    @patch("app.api.plan.read_first_interview_snapshot")
    def test_returns_cached_plan_when_refresh_generation_falls_back(
        self,
        read_snapshot,
        build_signature,
        read_cached,
        schedule_generation,
        generate_and_cache,
    ) -> None:
        cached_plan = build_plan()
        read_snapshot.return_value = self.snapshot
        build_signature.return_value = "test-signature"
        read_cached.return_value = cached_plan
        generate_and_cache.return_value = ("test-signature", None)

        result = get_personalized_plan(refresh=True, db=object(), current_user=self.current_user)

        self.assertEqual(result.signature, cached_plan.signature)
        schedule_generation.assert_called_once_with(self.current_user.id, self.snapshot, force=True)

    @patch("app.api.plan.schedule_personalized_plan_generation")
    @patch("app.api.plan.is_personalized_plan_generation_running")
    @patch("app.api.plan.read_cached_personalized_plan")
    @patch("app.api.plan.build_plan_signature")
    @patch("app.api.plan.read_first_interview_snapshot")
    def test_raises_503_when_generation_unavailable_and_cache_missing(
        self,
        read_snapshot,
        build_signature,
        read_cached,
        is_running,
        schedule_generation,
    ) -> None:
        read_snapshot.return_value = self.snapshot
        build_signature.return_value = "test-signature"
        read_cached.return_value = None
        is_running.return_value = False

        with self.assertRaises(HTTPException) as exc:
            get_personalized_plan(refresh=False, db=object(), current_user=self.current_user)

        self.assertEqual(exc.exception.status_code, 503)
        self.assertEqual(exc.exception.detail["code"], PLAN_GENERATION_UNAVAILABLE_CODE)
        schedule_generation.assert_called_once_with(self.current_user.id, self.snapshot)


if __name__ == "__main__":
    unittest.main()
