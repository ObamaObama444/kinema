from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from app.services.personalized_plan_jobs import schedule_personalized_plan_generation
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


class InlineThread:
    def __init__(self, target=None, name=None, daemon=None):
        self.target = target

    def start(self) -> None:
        if self.target:
            self.target()


class PlanGenerationJobsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = {
            "snapshot_version": "v1",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "data": {"main_goal": "lose_weight", "focus_area": "legs"},
        }

    @patch("app.services.personalized_plan_jobs.threading.Thread", InlineThread)
    @patch("app.services.personalized_plan_jobs.generate_personalized_plan")
    @patch("app.services.personalized_plan_jobs.write_cached_personalized_plan")
    @patch("app.services.personalized_plan_jobs.read_cached_personalized_plan")
    @patch("app.services.personalized_plan_jobs.build_plan_signature")
    def test_schedules_and_writes_complete_plan(
        self,
        build_signature,
        read_cached,
        write_cached,
        generate_plan,
    ) -> None:
        plan = build_plan()
        build_signature.return_value = "test-signature"
        read_cached.return_value = None
        generate_plan.return_value = plan

        signature, started = schedule_personalized_plan_generation(4, self.snapshot)

        self.assertEqual(signature, "test-signature")
        self.assertTrue(started)
        write_cached.assert_called_once_with(4, plan)

    @patch("app.services.personalized_plan_jobs.read_cached_personalized_plan")
    @patch("app.services.personalized_plan_jobs.build_plan_signature")
    def test_skips_schedule_when_cache_already_exists(
        self,
        build_signature,
        read_cached,
    ) -> None:
        build_signature.return_value = "test-signature"
        read_cached.return_value = build_plan()

        signature, started = schedule_personalized_plan_generation(4, self.snapshot)

        self.assertEqual(signature, "test-signature")
        self.assertFalse(started)


if __name__ == "__main__":
    unittest.main()
