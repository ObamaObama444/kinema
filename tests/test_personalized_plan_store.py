import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from app.schemas.plan import PersonalizedPlanResponse
from app.services.personalized_plan_store import read_cached_personalized_plan, write_cached_personalized_plan


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


class PersonalizedPlanStoreTests(unittest.TestCase):
    def test_write_and_read_valid_mistral_cache(self) -> None:
        plan = build_plan()
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("app.services.personalized_plan_store._plan_dir", return_value=Path(temp_dir)):
                write_cached_personalized_plan(4, plan)
                cached = read_cached_personalized_plan(4, plan.signature)

        self.assertIsNotNone(cached)
        self.assertEqual(cached.source, "mistral")
        self.assertEqual(len(cached.stages), 1)
        self.assertEqual(sum(len(stage.days) for stage in cached.stages), 10)

    def test_read_rejects_legacy_cache_without_schema_version(self) -> None:
        plan = build_plan()
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            path = base / "user_4_test-signature.json"
            path.write_text(json.dumps(plan.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
            with patch("app.services.personalized_plan_store._plan_dir", return_value=base):
                cached = read_cached_personalized_plan(4, "test-signature")

        self.assertIsNone(cached)

    def test_read_rejects_non_mistral_cache(self) -> None:
        plan = build_plan(source="fallback")
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("app.services.personalized_plan_store._plan_dir", return_value=Path(temp_dir)):
                path = Path(temp_dir) / "user_4_test-signature.json"
                payload = {
                    "schema_version": "v3",
                    "cached_at": datetime.now(timezone.utc).isoformat(),
                    "plan": plan.model_dump(mode="json"),
                }
                path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                cached = read_cached_personalized_plan(4, "test-signature")

        self.assertIsNone(cached)


if __name__ == "__main__":
    unittest.main()
