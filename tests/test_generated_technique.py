import unittest

from app.services.generated_technique import (
    build_reference_model,
    compare_generated_rep,
    sanitize_calibration_profile,
)


def generated_frames(kind: str) -> list[dict]:
    if kind == "reference":
        primary = [176, 173, 166, 152, 132, 108, 96, 110, 136, 156, 169, 176]
        secondary = [176, 172, 165, 150, 136, 118, 108, 120, 140, 157, 170, 176]
        depth = [0.94, 0.94, 0.92, 0.88, 0.81, 0.74, 0.69, 0.74, 0.82, 0.89, 0.93, 0.94]
        torso = [16, 17, 18, 20, 22, 24, 26, 24, 21, 19, 17, 16]
        posture = [11, 12, 13, 15, 17, 19, 21, 19, 16, 14, 12, 11]
        asymmetry = [2.0] * 12
        hip_asymmetry = [1.4] * 12
        heel = [0.01] * 12
        balance = [0.93, 0.93, 0.91, 0.87, 0.82, 0.76, 0.71, 0.76, 0.83, 0.89, 0.92, 0.93]
        view = [0.78] * 12
    elif kind == "perturbed":
        primary = [176, 174, 169, 158, 142, 122, 110, 124, 145, 159, 170, 176]
        secondary = [176, 173, 167, 155, 142, 126, 116, 128, 144, 158, 171, 176]
        depth = [0.94, 0.94, 0.93, 0.90, 0.85, 0.79, 0.74, 0.79, 0.85, 0.90, 0.93, 0.94]
        torso = [16, 18, 19, 22, 24, 27, 29, 27, 24, 21, 18, 16]
        posture = [11, 13, 14, 17, 19, 22, 24, 22, 19, 16, 13, 11]
        asymmetry = [5.0] * 12
        hip_asymmetry = [4.0] * 12
        heel = [0.01] * 12
        balance = [0.94, 0.94, 0.93, 0.91, 0.88, 0.84, 0.82, 0.85, 0.89, 0.92, 0.94, 0.94]
        view = [0.78] * 12
    elif kind == "heel_fail":
        primary = [176, 173, 166, 152, 132, 108, 96, 110, 136, 156, 169, 176]
        secondary = [176, 172, 165, 150, 136, 118, 108, 120, 140, 157, 170, 176]
        depth = [0.94, 0.94, 0.92, 0.88, 0.81, 0.74, 0.69, 0.74, 0.82, 0.89, 0.93, 0.94]
        torso = [16, 17, 18, 20, 22, 24, 26, 24, 21, 19, 17, 16]
        posture = [11, 12, 13, 15, 17, 19, 21, 19, 16, 14, 12, 11]
        asymmetry = [2.0] * 12
        hip_asymmetry = [1.4] * 12
        heel = [0.02, 0.03, 0.04, 0.06, 0.08, 0.10, 0.12, 0.10, 0.08, 0.06, 0.04, 0.03]
        balance = [0.93, 0.93, 0.91, 0.87, 0.82, 0.76, 0.71, 0.76, 0.83, 0.89, 0.92, 0.93]
        view = [0.78] * 12
    else:
        raise ValueError(f"Unknown generated frame kind: {kind}")

    return [
        {
            "timestamp_ms": index * 100,
            "primary_angle": primary_angle,
            "secondary_angle": secondary_angle,
            "depth_norm": depth_norm,
            "torso_angle": torso_angle,
            "asymmetry": asymmetry_value,
            "hip_asymmetry": hip_asymmetry_value,
            "side_view_score": view_value,
            "heel_lift_norm": heel_lift,
            "leg_angle": 180,
            "posture_tilt_deg": posture_tilt,
            "hip_ankle_vertical_norm": balance_shift,
        }
        for index, (
            primary_angle,
            secondary_angle,
            depth_norm,
            torso_angle,
            asymmetry_value,
            hip_asymmetry_value,
            view_value,
            heel_lift,
            posture_tilt,
            balance_shift,
        ) in enumerate(
            zip(
                primary,
                secondary,
                depth,
                torso,
                asymmetry,
                hip_asymmetry,
                view,
                heel,
                posture,
                balance,
            )
        )
    ]


class GeneratedTechniqueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference_model, self.calibration_profile = build_reference_model(
            frame_metrics=generated_frames("reference"),
            motion_family="squat_like",
            view_type="side",
            video_meta={"duration_ms": 1100, "width": 720, "height": 1280},
        )

    def test_reference_rep_scores_high(self) -> None:
        result = compare_generated_rep(
            frame_metrics=generated_frames("reference"),
            reference_model=self.reference_model,
            calibration_profile=self.calibration_profile,
            duration_ms=1100,
        )

        self.assertGreaterEqual(result["rep_score"], 96)
        self.assertEqual(result["quality"], "Отлично")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["details"]["hint_codes"], ["good_rep"])
        self.assertEqual(result["details"]["voice_feedback"]["code"], "good_rep")
        self.assertTrue(result["details"]["rule_flags"]["good_rep"])

    def test_strict_calibration_is_harsher_than_standard(self) -> None:
        standard_result = compare_generated_rep(
            frame_metrics=generated_frames("perturbed"),
            reference_model=self.reference_model,
            calibration_profile=self.calibration_profile,
            duration_ms=1100,
        )
        strict_profile = sanitize_calibration_profile(
            {"preset": "strict"},
            motion_family="squat_like",
            reference_model=self.reference_model,
        )
        strict_result = compare_generated_rep(
            frame_metrics=generated_frames("perturbed"),
            reference_model=self.reference_model,
            calibration_profile=strict_profile,
            duration_ms=1100,
        )

        self.assertLess(strict_result["rep_score"], standard_result["rep_score"])
        self.assertLess(
            strict_result["details"]["scores"]["posture"],
            standard_result["details"]["scores"]["posture"],
        )

    def test_heel_lift_cap_is_applied(self) -> None:
        result = compare_generated_rep(
            frame_metrics=generated_frames("heel_fail"),
            reference_model=self.reference_model,
            calibration_profile=self.calibration_profile,
            duration_ms=1100,
        )

        self.assertIn("heel_lift", result["details"]["caps_applied"])
        self.assertIn("Потеря опоры / отрыв пятки", result["errors"])
        self.assertIn("heel_lift", result["details"]["hint_codes"])
        self.assertEqual(result["details"]["voice_feedback"]["code"], "heel_lift")
        self.assertTrue(result["details"]["rule_flags"]["heel_lift"])
        self.assertLessEqual(
            result["rep_score"],
            int(self.calibration_profile["caps"]["severe_heel_lift_max_score"]),
        )


if __name__ == "__main__":
    unittest.main()
