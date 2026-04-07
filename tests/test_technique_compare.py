import unittest

from app.services.technique_compare import compare_pushup_rep, compare_squat_rep


def squat_frames(kind: str) -> list[dict]:
    if kind == "excellent":
        primary = [176, 170, 158, 128, 95, 126, 160, 176]
        secondary = [176, 168, 150, 122, 105, 122, 152, 176]
        depth = [0.95, 0.95, 0.93, 0.84, 0.71, 0.84, 0.93, 0.95]
        torso = [16, 18, 22, 24, 26, 24, 20, 17]
        heel = [0.01] * 8
    elif kind == "heel_fail":
        primary = [176, 170, 158, 128, 95, 126, 160, 176]
        secondary = [176, 168, 150, 122, 105, 122, 152, 176]
        depth = [0.95, 0.95, 0.93, 0.84, 0.70, 0.84, 0.93, 0.95]
        torso = [16, 18, 22, 24, 27, 24, 20, 17]
        heel = [0.01, 0.01, 0.02, 0.08, 0.14, 0.13, 0.08, 0.02]
    elif kind == "heel_noise":
        primary = [176, 170, 158, 128, 95, 126, 160, 176]
        secondary = [176, 168, 150, 122, 105, 122, 152, 176]
        depth = [0.95, 0.95, 0.93, 0.84, 0.71, 0.84, 0.93, 0.95]
        torso = [16, 18, 22, 24, 26, 24, 20, 17]
        heel = [0.07, 0.07, 0.08, 0.09, 0.09, 0.08, 0.07, 0.07]
    elif kind == "undersquat_severe":
        primary = [176, 174, 170, 158, 145, 142, 160, 176]
        secondary = [176, 174, 168, 156, 146, 145, 160, 176]
        depth = [0.95, 0.95, 0.94, 0.91, 0.88, 0.89, 0.92, 0.95]
        torso = [16, 17, 18, 20, 22, 21, 18, 17]
        heel = [0.01] * 8
    elif kind == "undersquat_regular":
        primary = [176, 172, 166, 150, 115, 126, 160, 176]
        secondary = [176, 171, 164, 145, 118, 125, 160, 176]
        depth = [0.95, 0.95, 0.94, 0.89, 0.77, 0.83, 0.92, 0.95]
        torso = [16, 18, 20, 23, 26, 24, 20, 18]
        heel = [0.01] * 8
    else:
        raise ValueError(f"Unknown squat frame kind: {kind}")

    return [
        {
            "primary_angle": primary_angle,
            "secondary_angle": secondary_angle,
            "depth_norm": depth_norm,
            "torso_angle": torso_angle,
            "asymmetry": 1.5,
            "hip_asymmetry": 1.0,
            "side_view_score": 0.78,
            "heel_lift_norm": heel_lift,
            "leg_angle": 180,
        }
        for primary_angle, secondary_angle, depth_norm, torso_angle, heel_lift in zip(
            primary, secondary, depth, torso, heel
        )
    ]


def pushup_frames(kind: str) -> list[dict]:
    if kind == "perfect":
        primary = [176, 168, 150, 118, 86, 118, 152, 176]
        secondary = [178, 178, 177, 176, 175, 176, 177, 178]
        depth = [0.84, 0.84, 0.80, 0.72, 0.62, 0.72, 0.80, 0.84]
        torso = [3, 4, 5, 6, 7, 6, 5, 4]
        leg = [176] * 8
        asymmetry = [1.5] * 8
    elif kind == "penalized":
        primary = [176, 172, 165, 154, 142, 152, 165, 176]
        secondary = [176, 174, 170, 166, 160, 164, 170, 176]
        depth = [0.84, 0.84, 0.82, 0.80, 0.77, 0.79, 0.82, 0.84]
        torso = [8, 10, 12, 14, 18, 16, 12, 10]
        leg = [124, 124, 122, 120, 118, 120, 122, 124]
        asymmetry = [9] * 8
    else:
        raise ValueError(f"Unknown pushup frame kind: {kind}")

    return [
        {
            "primary_angle": primary_angle,
            "secondary_angle": secondary_angle,
            "depth_norm": depth_norm,
            "torso_angle": torso_angle,
            "asymmetry": asymmetry_value,
            "hip_asymmetry": asymmetry_value / 2,
            "side_view_score": 0.78,
            "heel_lift_norm": 0.01,
            "leg_angle": leg_angle,
        }
        for primary_angle, secondary_angle, depth_norm, torso_angle, leg_angle, asymmetry_value in zip(
            primary, secondary, depth, torso, leg, asymmetry
        )
    ]


class TechniqueCompareTests(unittest.TestCase):
    def test_squat_breakdown_contains_weighted_penalties_and_voice_feedback(self) -> None:
        result = compare_squat_rep(squat_frames("heel_fail"))

        issue_codes = {
            item["code"]
            for item in result.details["score_breakdown"]["issue_penalties"]
        }

        self.assertIn("heel_lift", issue_codes)
        self.assertEqual(result.details["score_breakdown"]["base_score"], 100.0)
        self.assertEqual(
            result.details["voice_feedback"]["message"],
            "Не отрывайте пятки от пола.",
        )

    def test_squat_heel_fail_forces_score_one(self) -> None:
        result = compare_squat_rep(squat_frames("heel_fail"))

        self.assertEqual(result.rep_score, 1)
        self.assertTrue(result.details["heel_fail"])
        self.assertIn("Отрыв пяток", " ".join(result.errors))

    def test_squat_flat_heel_noise_does_not_trigger_heel_fail(self) -> None:
        result = compare_squat_rep(squat_frames("heel_noise"))

        self.assertFalse(result.details["heel_fail"])
        self.assertNotIn("heel_lift", result.details["hint_codes"])
        self.assertNotEqual(result.details["voice_feedback"]["code"], "heel_lift")
        self.assertGreater(result.rep_score, 1)

    def test_squat_severe_undersquat_is_capped(self) -> None:
        result = compare_squat_rep(squat_frames("undersquat_severe"))

        self.assertTrue(result.details["undersquat_severe"])
        self.assertLessEqual(result.rep_score, 30)

    def test_squat_regular_undersquat_is_capped_to_forty(self) -> None:
        result = compare_squat_rep(squat_frames("undersquat_regular"))

        self.assertTrue(result.details["undersquat"])
        self.assertFalse(result.details["undersquat_severe"])
        self.assertLessEqual(result.rep_score, 40)
        self.assertEqual(result.details["voice_feedback"]["code"], "undersquat")
        self.assertEqual(
            result.details["voice_feedback"]["message"],
            "Добавьте глубину приседа.",
        )

    def test_squat_excellent_pose_keeps_floor_above_ninety_two(self) -> None:
        result = compare_squat_rep(squat_frames("excellent"))

        self.assertTrue(result.details["excellent_pose"])
        self.assertGreaterEqual(result.rep_score, 92)
        self.assertEqual(result.details["voice_feedback"]["code"], "good_rep")
        self.assertEqual(
            result.details["voice_feedback"]["message"],
            "Ты молодец, так держать.",
        )

    def test_pushup_perfect_rep_scores_hundred(self) -> None:
        result = compare_pushup_rep(pushup_frames("perfect"))

        self.assertEqual(result.rep_score, 100)
        self.assertEqual(result.quality, "Отлично")
        self.assertEqual(result.details["voice_feedback"]["code"], "good_rep")
        self.assertEqual(
            result.details["voice_feedback"]["message"],
            "Ты молодец, так держать.",
        )

    def test_pushup_bent_legs_and_shallow_depth_are_penalized(self) -> None:
        result = compare_pushup_rep(pushup_frames("penalized"))

        self.assertLess(result.rep_score, 70)
        self.assertIn("Недостаточная глубина", result.errors)
        self.assertIn("Сильное сгибание ног", result.errors)

    def test_pushup_breakdown_penalizes_body_line(self) -> None:
        result = compare_pushup_rep(pushup_frames("penalized"))

        issue_penalties = {
            item["code"]: item["penalty"]
            for item in result.details["score_breakdown"]["issue_penalties"]
        }

        self.assertEqual(result.details["score_breakdown"]["base_score"], 100.0)
        self.assertGreater(issue_penalties.get("body_line_break", 0), 0)


if __name__ == "__main__":
    unittest.main()
