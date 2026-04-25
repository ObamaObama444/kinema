from __future__ import annotations

import json
import math
import re
from statistics import mean
from typing import Any


SUPPORTED_MOTION_FAMILIES = {
    "squat_like": "Приседание",
    "lunge_like": "Выпад / шаг",
    "hinge_like": "Наклон / таз назад",
    "push_like": "Жим / отжимание",
    "core_like": "Пресс / корпус",
}

SUPPORTED_VIEW_TYPES = {
    "side": "Боковой",
    "front": "Фронтальный",
    "three_quarter": "3/4",
}

REFERENCE_CURVE_POINTS = 60

_DEFAULT_CALIBRATION_BY_FAMILY: dict[str, dict[str, Any]] = {
    "squat_like": {
        "weights": {
            "trajectory": 0.37,
            "range_of_motion": 0.24,
            "posture": 0.16,
            "symmetry": 0.11,
            "stability": 0.07,
            "tempo": 0.05,
        },
        "tolerances": {
            "curve_mae": 0.18,
            "range_ratio_low": 0.82,
            "range_ratio_high": 1.18,
            "torso_tilt_deg": 12.0,
            "asymmetry_pct": 14.0,
            "heel_lift_norm": 0.045,
            "stability_norm": 0.12,
            "tempo_ratio_pct": 0.24,
            "view_quality_min": 0.45,
        },
        "caps": {
            "bad_view_max_score": 65,
            "severe_range_max_score": 45,
            "severe_posture_max_score": 55,
            "severe_asymmetry_max_score": 60,
            "severe_heel_lift_max_score": 50,
        },
    },
    "lunge_like": {
        "weights": {
            "trajectory": 0.36,
            "range_of_motion": 0.25,
            "posture": 0.15,
            "symmetry": 0.12,
            "stability": 0.07,
            "tempo": 0.05,
        },
        "tolerances": {
            "curve_mae": 0.2,
            "range_ratio_low": 0.8,
            "range_ratio_high": 1.2,
            "torso_tilt_deg": 13.0,
            "asymmetry_pct": 16.0,
            "heel_lift_norm": 0.05,
            "stability_norm": 0.13,
            "tempo_ratio_pct": 0.26,
            "view_quality_min": 0.42,
        },
        "caps": {
            "bad_view_max_score": 68,
            "severe_range_max_score": 48,
            "severe_posture_max_score": 58,
            "severe_asymmetry_max_score": 62,
            "severe_heel_lift_max_score": 52,
        },
    },
    "hinge_like": {
        "weights": {
            "trajectory": 0.34,
            "range_of_motion": 0.22,
            "posture": 0.21,
            "symmetry": 0.1,
            "stability": 0.08,
            "tempo": 0.05,
        },
        "tolerances": {
            "curve_mae": 0.19,
            "range_ratio_low": 0.82,
            "range_ratio_high": 1.16,
            "torso_tilt_deg": 10.0,
            "asymmetry_pct": 13.0,
            "heel_lift_norm": 0.04,
            "stability_norm": 0.11,
            "tempo_ratio_pct": 0.22,
            "view_quality_min": 0.45,
        },
        "caps": {
            "bad_view_max_score": 65,
            "severe_range_max_score": 50,
            "severe_posture_max_score": 50,
            "severe_asymmetry_max_score": 62,
            "severe_heel_lift_max_score": 55,
        },
    },
    "push_like": {
        "weights": {
            "trajectory": 0.39,
            "range_of_motion": 0.22,
            "posture": 0.15,
            "symmetry": 0.11,
            "stability": 0.08,
            "tempo": 0.05,
        },
        "tolerances": {
            "curve_mae": 0.18,
            "range_ratio_low": 0.8,
            "range_ratio_high": 1.2,
            "torso_tilt_deg": 11.0,
            "asymmetry_pct": 13.0,
            "heel_lift_norm": 0.035,
            "stability_norm": 0.11,
            "tempo_ratio_pct": 0.22,
            "view_quality_min": 0.44,
        },
        "caps": {
            "bad_view_max_score": 65,
            "severe_range_max_score": 45,
            "severe_posture_max_score": 52,
            "severe_asymmetry_max_score": 60,
            "severe_heel_lift_max_score": 55,
        },
    },
    "core_like": {
        "weights": {
            "trajectory": 0.34,
            "range_of_motion": 0.24,
            "posture": 0.16,
            "symmetry": 0.1,
            "stability": 0.1,
            "tempo": 0.06,
        },
        "tolerances": {
            "curve_mae": 0.22,
            "range_ratio_low": 0.78,
            "range_ratio_high": 1.22,
            "torso_tilt_deg": 14.0,
            "asymmetry_pct": 18.0,
            "heel_lift_norm": 0.04,
            "stability_norm": 0.14,
            "tempo_ratio_pct": 0.28,
            "view_quality_min": 0.4,
        },
        "caps": {
            "bad_view_max_score": 70,
            "severe_range_max_score": 48,
            "severe_posture_max_score": 58,
            "severe_asymmetry_max_score": 65,
            "severe_heel_lift_max_score": 60,
        },
    },
}


def motion_family_label(value: str) -> str:
    return SUPPORTED_MOTION_FAMILIES.get(str(value or "").strip().lower(), "Пользовательское")


def view_type_label(value: str) -> str:
    return SUPPORTED_VIEW_TYPES.get(str(value or "").strip().lower(), "Свободный ракурс")


def dump_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def load_json(payload: str | None, fallback: Any) -> Any:
    if not payload:
        return fallback
    try:
        return json.loads(payload)
    except (TypeError, ValueError):
        return fallback


def slugify_title(title: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ]+", "-", str(title or "").strip().lower())
    normalized = normalized.strip("-")
    return normalized or "custom-exercise"


def build_catalog_tags(profile: Any) -> list[str]:
    tags = [
        "Системный эталон" if bool(getattr(profile, "is_system", False)) else "Пользовательский эталон",
        motion_family_label(getattr(profile, "motion_family", "")),
        view_type_label(getattr(profile, "view_type", "")),
    ]
    return [tag for tag in tags if tag]


def _safe_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _score_label(score: int) -> str:
    if score >= 85:
        return "Отлично"
    if score >= 60:
        return "Нормально"
    return "Нужно улучшить"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * (pct / 100.0)
    left = int(position)
    right = min(left + 1, len(ordered) - 1)
    if left == right:
        return ordered[left]
    weight = position - left
    return ordered[left] * (1.0 - weight) + ordered[right] * weight


def _resample(values: list[float], points: int) -> list[float]:
    if not values:
        return [0.0] * points
    if len(values) == 1:
        return [values[0]] * points

    result: list[float] = []
    last_index = len(values) - 1
    for point_index in range(points):
        position = last_index * (point_index / max(points - 1, 1))
        left = int(math.floor(position))
        right = min(left + 1, last_index)
        if left == right:
            result.append(values[left])
            continue
        weight = position - left
        result.append(values[left] * (1.0 - weight) + values[right] * weight)
    return result


def _series_baseline(values: list[float]) -> float:
    if not values:
        return 0.0
    head = max(1, len(values) // 8)
    baseline_samples = values[:head] + values[-head:]
    return mean(baseline_samples)


def _series_amplitude(values: list[float]) -> float:
    if not values:
        return 0.0
    baseline = _series_baseline(values)
    return max(abs(value - baseline) for value in values)


def _progress_curve(values: list[float]) -> list[float]:
    if not values:
        return []
    baseline = _series_baseline(values)
    amplitude = max(_series_amplitude(values), 1e-6)
    return [_clamp(abs(value - baseline) / amplitude, 0.0, 1.3) for value in values]


def _smoothness_norm(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    deltas = [values[index] - values[index - 1] for index in range(1, len(values))]
    if len(deltas) < 2:
        return 0.0
    jerks = [abs(deltas[index] - deltas[index - 1]) for index in range(1, len(deltas))]
    return mean(jerks) if jerks else 0.0


def _normalize_frames(frame_metrics: list[dict[str, Any]]) -> list[dict[str, float]]:
    normalized: list[dict[str, float]] = []
    for item in frame_metrics:
        row = {
            "timestamp_ms": _safe_float(item.get("timestamp_ms"), 0.0),
            "primary_angle": _safe_float(item.get("primary_angle"), 0.0),
            "secondary_angle": _safe_float(item.get("secondary_angle"), 0.0),
            "depth_norm": _safe_float(item.get("depth_norm"), 0.0),
            "torso_angle": _safe_float(item.get("torso_angle"), 0.0),
            "asymmetry": _safe_float(item.get("asymmetry"), 0.0),
            "hip_asymmetry": _safe_float(item.get("hip_asymmetry"), 0.0),
            "side_view_score": _safe_float(item.get("side_view_score"), 0.0),
            "heel_lift_norm": _safe_float(item.get("heel_lift_norm"), 0.0),
            "leg_angle": _safe_float(item.get("leg_angle"), 180.0),
            "posture_tilt_deg": _safe_float(item.get("posture_tilt_deg"), 0.0),
            "hip_ankle_vertical_norm": _safe_float(item.get("hip_ankle_vertical_norm"), 0.0),
        }
        normalized.append(row)
    return normalized


def _analyze_frame_metrics(
    frame_metrics: list[dict[str, Any]],
    *,
    duration_ms: int | None,
) -> dict[str, Any]:
    frames = _normalize_frames(frame_metrics)
    if len(frames) < 10:
        raise ValueError("Недостаточно кадров для построения эталонной модели.")

    primary = [row["primary_angle"] for row in frames]
    secondary = [row["secondary_angle"] for row in frames]
    depth = [row["depth_norm"] for row in frames]
    torso = [row["torso_angle"] for row in frames]
    asymmetry = [row["asymmetry"] for row in frames]
    hip_asymmetry = [row["hip_asymmetry"] for row in frames]
    heel = [max(0.0, row["heel_lift_norm"]) for row in frames]
    leg = [row["leg_angle"] for row in frames]
    view_quality = [row["side_view_score"] for row in frames]
    posture_tilt = [row["posture_tilt_deg"] for row in frames]
    balance_shift = [row["hip_ankle_vertical_norm"] for row in frames]

    detected_duration_ms = int(duration_ms or 0)
    if detected_duration_ms <= 0 and len(frames) > 1:
        timestamps = [row["timestamp_ms"] for row in frames if row["timestamp_ms"] > 0]
        if len(timestamps) >= 2:
            detected_duration_ms = int(max(timestamps) - min(timestamps))

    primary_progress = _progress_curve(primary)
    secondary_progress = _progress_curve(secondary)
    depth_progress = _progress_curve(depth)
    torso_progress = _progress_curve(torso)

    primary_amp = _series_amplitude(primary)
    secondary_amp = _series_amplitude(secondary)
    depth_amp = _series_amplitude(depth)

    return {
        "frame_count": len(frames),
        "duration_ms": detected_duration_ms,
        "curves": {
            "primary_progress": _resample(primary_progress, REFERENCE_CURVE_POINTS),
            "secondary_progress": _resample(secondary_progress, REFERENCE_CURVE_POINTS),
            "depth_progress": _resample(depth_progress, REFERENCE_CURVE_POINTS),
            "torso_progress": _resample(torso_progress, REFERENCE_CURVE_POINTS),
        },
        "summary": {
            "primary_amplitude": round(primary_amp, 4),
            "secondary_amplitude": round(secondary_amp, 4),
            "depth_amplitude": round(depth_amp, 4),
            "primary_min": round(min(primary), 4),
            "primary_max": round(max(primary), 4),
            "secondary_min": round(min(secondary), 4),
            "secondary_max": round(max(secondary), 4),
            "depth_min": round(min(depth), 4),
            "depth_max": round(max(depth), 4),
            "mean_torso_angle": round(mean(torso), 4),
            "p90_torso_angle": round(_percentile(torso, 90), 4),
            "mean_posture_tilt_deg": round(mean(posture_tilt), 4),
            "p90_posture_tilt_deg": round(_percentile(posture_tilt, 90), 4),
            "mean_asymmetry": round(mean(asymmetry), 4),
            "p90_asymmetry": round(_percentile(asymmetry, 90), 4),
            "mean_hip_asymmetry": round(mean(hip_asymmetry), 4),
            "p90_hip_asymmetry": round(_percentile(hip_asymmetry, 90), 4),
            "mean_heel_lift": round(mean(heel), 4),
            "p90_heel_lift": round(_percentile(heel, 90), 4),
            "mean_leg_angle": round(mean(leg), 4),
            "mean_view_quality": round(mean(view_quality), 4),
            "mean_balance_shift": round(mean(balance_shift), 4),
            "smoothness_norm": round(
                mean(
                    [
                        _smoothness_norm(primary_progress),
                        _smoothness_norm(secondary_progress),
                        _smoothness_norm(depth_progress),
                    ]
                ),
                6,
            ),
        },
    }


def default_calibration_profile(
    *,
    motion_family: str,
    reference_model: dict[str, Any],
    preset: str = "standard",
) -> dict[str, Any]:
    family = motion_family if motion_family in _DEFAULT_CALIBRATION_BY_FAMILY else "squat_like"
    base = json.loads(dump_json(_DEFAULT_CALIBRATION_BY_FAMILY[family]))
    tolerances = base["tolerances"]

    if preset == "soft":
        tolerances["curve_mae"] = round(tolerances["curve_mae"] * 1.2, 4)
        tolerances["torso_tilt_deg"] = round(tolerances["torso_tilt_deg"] * 1.2, 4)
        tolerances["asymmetry_pct"] = round(tolerances["asymmetry_pct"] * 1.18, 4)
        tolerances["tempo_ratio_pct"] = round(tolerances["tempo_ratio_pct"] * 1.18, 4)
        tolerances["range_ratio_low"] = round(max(0.6, tolerances["range_ratio_low"] - 0.04), 4)
        tolerances["range_ratio_high"] = round(tolerances["range_ratio_high"] + 0.05, 4)
    elif preset == "strict":
        tolerances["curve_mae"] = round(tolerances["curve_mae"] * 0.82, 4)
        tolerances["torso_tilt_deg"] = round(tolerances["torso_tilt_deg"] * 0.84, 4)
        tolerances["asymmetry_pct"] = round(tolerances["asymmetry_pct"] * 0.84, 4)
        tolerances["tempo_ratio_pct"] = round(tolerances["tempo_ratio_pct"] * 0.86, 4)
        tolerances["range_ratio_low"] = round(min(0.92, tolerances["range_ratio_low"] + 0.04), 4)
        tolerances["range_ratio_high"] = round(max(1.04, tolerances["range_ratio_high"] - 0.04), 4)

    reference_summary = reference_model.get("summary", {})
    mean_view_quality = _safe_float(reference_summary.get("mean_view_quality"), tolerances["view_quality_min"])
    tolerances["view_quality_min"] = round(min(tolerances["view_quality_min"], mean_view_quality * 0.96), 4)

    return {
        "preset": preset,
        "weights": base["weights"],
        "tolerances": tolerances,
        "caps": base["caps"],
    }


def sanitize_calibration_profile(
    calibration_profile: dict[str, Any] | None,
    *,
    motion_family: str,
    reference_model: dict[str, Any],
) -> dict[str, Any]:
    source = calibration_profile or {}
    preset = str(source.get("preset") or "standard").strip().lower()
    if preset not in {"soft", "standard", "strict"}:
        preset = "standard"

    base = default_calibration_profile(
        motion_family=motion_family,
        reference_model=reference_model,
        preset=preset,
    )

    weights = source.get("weights") if isinstance(source.get("weights"), dict) else {}
    tolerances = source.get("tolerances") if isinstance(source.get("tolerances"), dict) else {}
    caps = source.get("caps") if isinstance(source.get("caps"), dict) else {}

    for key in base["weights"]:
        base["weights"][key] = round(_clamp(_safe_float(weights.get(key), base["weights"][key]), 0.0, 1.0), 4)

    for key, bounds in {
        "curve_mae": (0.05, 0.55),
        "range_ratio_low": (0.55, 1.0),
        "range_ratio_high": (1.0, 1.6),
        "torso_tilt_deg": (3.0, 35.0),
        "asymmetry_pct": (2.0, 40.0),
        "heel_lift_norm": (0.0, 0.25),
        "stability_norm": (0.01, 0.4),
        "tempo_ratio_pct": (0.05, 0.8),
        "view_quality_min": (0.1, 0.95),
    }.items():
        base["tolerances"][key] = round(
            _clamp(_safe_float(tolerances.get(key), base["tolerances"][key]), bounds[0], bounds[1]),
            4,
        )

    for key, bounds in {
        "bad_view_max_score": (20.0, 100.0),
        "severe_range_max_score": (10.0, 100.0),
        "severe_posture_max_score": (10.0, 100.0),
        "severe_asymmetry_max_score": (10.0, 100.0),
        "severe_heel_lift_max_score": (10.0, 100.0),
    }.items():
        base["caps"][key] = round(
            _clamp(_safe_float(caps.get(key), base["caps"][key]), bounds[0], bounds[1]),
            2,
        )

    total_weight = sum(base["weights"].values())
    if total_weight <= 1e-6:
        total_weight = 1.0
    for key in list(base["weights"].keys()):
        base["weights"][key] = round(base["weights"][key] / total_weight, 4)

    return base


def build_reference_model(
    *,
    frame_metrics: list[dict[str, Any]],
    motion_family: str,
    view_type: str,
    video_meta: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if motion_family not in SUPPORTED_MOTION_FAMILIES:
        raise ValueError("Неподдерживаемое семейство движения.")
    if view_type not in SUPPORTED_VIEW_TYPES:
        raise ValueError("Неподдерживаемый ракурс.")

    parsed_video_meta = video_meta or {}
    duration_ms = int(_safe_float(parsed_video_meta.get("duration_ms"), 0))
    analysis = _analyze_frame_metrics(frame_metrics, duration_ms=duration_ms)
    reference_model = {
        "version": 1,
        "motion_family": motion_family,
        "view_type": view_type,
        "curve_points": REFERENCE_CURVE_POINTS,
        "frame_count": analysis["frame_count"],
        "duration_ms": analysis["duration_ms"],
        "video_meta": {
            "duration_ms": duration_ms or analysis["duration_ms"],
            "width": int(_safe_float(parsed_video_meta.get("width"), 0)),
            "height": int(_safe_float(parsed_video_meta.get("height"), 0)),
            "size_bytes": int(_safe_float(parsed_video_meta.get("size_bytes"), 0)),
        },
        "curves": analysis["curves"],
        "summary": analysis["summary"],
        "metric_labels": {
            "primary": "Основная траектория",
            "secondary": "Вторичная траектория",
            "depth": "Амплитуда",
            "torso": "Положение корпуса",
            "symmetry": "Симметрия",
            "stability": "Стабильность",
            "tempo": "Темп",
        },
    }
    calibration = default_calibration_profile(
        motion_family=motion_family,
        reference_model=reference_model,
        preset="standard",
    )
    return reference_model, calibration


def _mae(values_a: list[float], values_b: list[float]) -> float:
    if not values_a or not values_b:
        return 1.0
    count = min(len(values_a), len(values_b))
    return sum(abs(values_a[index] - values_b[index]) for index in range(count)) / count


def _score_from_error(error: float, tolerance: float) -> float:
    safe_tolerance = max(tolerance, 1e-6)
    normalized = _clamp(error / safe_tolerance, 0.0, 2.2)
    return 100.0 * (1.0 - _clamp(normalized / 1.4, 0.0, 1.0)) ** 1.12


def _score_from_ratio(ratio: float, low: float, high: float) -> float:
    safe_ratio = max(ratio, 1e-6)
    if low <= safe_ratio <= high:
        center = (low + high) / 2.0
        distance = abs(safe_ratio - center) / max(high - low, 1e-6)
        return 100.0 - min(distance * 22.0, 18.0)
    if safe_ratio < low:
        deficit = (low - safe_ratio) / max(low, 1e-6)
        return max(0.0, 100.0 - deficit * 130.0)
    excess = (safe_ratio - high) / max(high, 1e-6)
    return max(0.0, 100.0 - excess * 125.0)


def _generated_hint_context(
    *,
    motion_family: str,
    rep_score: int,
    caps_applied: list[str],
    lowest_bucket: str,
) -> tuple[list[str], dict[str, Any], dict[str, bool]]:
    family_name = {
        "squat_like": "приседа",
        "lunge_like": "выпада",
        "push_like": "отжимания",
        "core_like": "движения корпуса",
        "hinge_like": "наклона",
    }.get(motion_family, "движения")
    voice_map = {
        "camera_side_view": {
            "message": "Повернитесь боком к камере и оставьте всё тело в кадре.",
            "priority": "high",
        },
        "partial_range": {
            "message": f"Верните амплитуду {family_name} ближе к эталону.",
            "priority": "med",
        },
        "body_alignment": {
            "message": f"Стабилизируйте корпус и держите форму {family_name} ровнее.",
            "priority": "med",
        },
        "asymmetry": {
            "message": "Выравняйте стороны и уберите перекос движения.",
            "priority": "med",
        },
        "heel_lift": {
            "message": "Сохраняйте полную опору и не отрывайте пятку.",
            "priority": "high",
        },
        "instability": {
            "message": "Сделайте повтор плавнее, без рывков.",
            "priority": "med",
        },
        "tempo_control": {
            "message": "Вернитесь к ровному темпу и не спешите.",
            "priority": "low",
        },
        "good_rep": {
            "message": "Чистый повтор, держите ту же технику.",
            "priority": "low",
        },
    }
    hint_codes: list[str] = []

    if "bad_view" in caps_applied:
        hint_codes.append("camera_side_view")
    if "range" in caps_applied:
        hint_codes.append("partial_range")
    if "posture" in caps_applied:
        hint_codes.append("body_alignment")
    if "asymmetry" in caps_applied:
        hint_codes.append("asymmetry")
    if "heel_lift" in caps_applied:
        hint_codes.append("heel_lift")

    bucket_to_code = {
        "trajectory": "partial_range",
        "range": "partial_range",
        "posture": "body_alignment",
        "symmetry": "asymmetry",
        "stability": "instability",
        "tempo": "tempo_control",
    }
    if not hint_codes:
        hint_codes.append(bucket_to_code.get(lowest_bucket, "tempo_control"))

    if rep_score >= 85 and not caps_applied:
        hint_codes = ["good_rep"]

    primary_code = hint_codes[0] if hint_codes else "good_rep"
    voice_template = voice_map.get(primary_code, voice_map["good_rep"])
    rule_flags = {
        "bad_view": "bad_view" in caps_applied,
        "partial_range": "range" in caps_applied or primary_code == "partial_range",
        "body_alignment": "posture" in caps_applied or primary_code == "body_alignment",
        "asymmetry": "asymmetry" in caps_applied or primary_code == "asymmetry",
        "heel_lift": "heel_lift" in caps_applied or primary_code == "heel_lift",
        "good_rep": primary_code == "good_rep",
    }
    voice_feedback = {
        "code": primary_code,
        "message": str(voice_template["message"]),
        "priority": str(voice_template["priority"]),
    }
    return list(dict.fromkeys(hint_codes)), voice_feedback, rule_flags


def compare_generated_rep(
    *,
    frame_metrics: list[dict[str, Any]],
    reference_model: dict[str, Any],
    calibration_profile: dict[str, Any],
    duration_ms: int | None = None,
) -> dict[str, Any]:
    analysis = _analyze_frame_metrics(frame_metrics, duration_ms=duration_ms)
    calibration = sanitize_calibration_profile(
        calibration_profile,
        motion_family=str(reference_model.get("motion_family") or "squat_like"),
        reference_model=reference_model,
    )
    reference_curves = reference_model.get("curves", {})
    reference_summary = reference_model.get("summary", {})

    primary_curve_error = _mae(analysis["curves"]["primary_progress"], reference_curves.get("primary_progress", []))
    secondary_curve_error = _mae(analysis["curves"]["secondary_progress"], reference_curves.get("secondary_progress", []))
    depth_curve_error = _mae(analysis["curves"]["depth_progress"], reference_curves.get("depth_progress", []))
    torso_curve_error = _mae(analysis["curves"]["torso_progress"], reference_curves.get("torso_progress", []))
    trajectory_score = mean(
        [
            _score_from_error(primary_curve_error, calibration["tolerances"]["curve_mae"]),
            _score_from_error(secondary_curve_error, calibration["tolerances"]["curve_mae"]),
            _score_from_error(depth_curve_error, calibration["tolerances"]["curve_mae"]),
        ]
    )

    primary_ratio = _safe_float(analysis["summary"].get("primary_amplitude"), 0.0) / max(
        _safe_float(reference_summary.get("primary_amplitude"), 1.0),
        1e-6,
    )
    secondary_ratio = _safe_float(analysis["summary"].get("secondary_amplitude"), 0.0) / max(
        _safe_float(reference_summary.get("secondary_amplitude"), 1.0),
        1e-6,
    )
    depth_ratio = _safe_float(analysis["summary"].get("depth_amplitude"), 0.0) / max(
        _safe_float(reference_summary.get("depth_amplitude"), 1.0),
        1e-6,
    )
    range_score = mean(
        [
            _score_from_ratio(primary_ratio, calibration["tolerances"]["range_ratio_low"], calibration["tolerances"]["range_ratio_high"]),
            _score_from_ratio(secondary_ratio, calibration["tolerances"]["range_ratio_low"], calibration["tolerances"]["range_ratio_high"]),
            _score_from_ratio(depth_ratio, calibration["tolerances"]["range_ratio_low"], calibration["tolerances"]["range_ratio_high"]),
        ]
    )

    posture_delta = abs(
        _safe_float(analysis["summary"].get("p90_posture_tilt_deg"), 0.0)
        - _safe_float(reference_summary.get("p90_posture_tilt_deg"), 0.0)
    )
    posture_score = _score_from_error(posture_delta, calibration["tolerances"]["torso_tilt_deg"])

    asymmetry_delta = max(
        0.0,
        _safe_float(analysis["summary"].get("mean_asymmetry"), 0.0)
        - _safe_float(reference_summary.get("mean_asymmetry"), 0.0),
        _safe_float(analysis["summary"].get("mean_hip_asymmetry"), 0.0)
        - _safe_float(reference_summary.get("mean_hip_asymmetry"), 0.0),
    )
    symmetry_score = _score_from_error(asymmetry_delta, calibration["tolerances"]["asymmetry_pct"])

    stability_delta = abs(
        _safe_float(analysis["summary"].get("smoothness_norm"), 0.0)
        - _safe_float(reference_summary.get("smoothness_norm"), 0.0)
    )
    stability_score = _score_from_error(stability_delta, calibration["tolerances"]["stability_norm"])

    reference_duration = max(_safe_float(reference_model.get("duration_ms"), 0.0), 1.0)
    duration_ratio = max(_safe_float(analysis.get("duration_ms"), 0.0), 1.0) / reference_duration
    tempo_score = _score_from_error(
        abs(duration_ratio - 1.0),
        calibration["tolerances"]["tempo_ratio_pct"],
    )

    weights = calibration["weights"]
    score_float = (
        trajectory_score * weights["trajectory"]
        + range_score * weights["range_of_motion"]
        + posture_score * weights["posture"]
        + symmetry_score * weights["symmetry"]
        + stability_score * weights["stability"]
        + tempo_score * weights["tempo"]
    )

    errors: list[str] = []
    tips: list[str] = []
    caps_applied: list[str] = []
    lowest_bucket = min(
        [
            ("trajectory", trajectory_score),
            ("range", range_score),
            ("posture", posture_score),
            ("symmetry", symmetry_score),
            ("stability", stability_score),
            ("tempo", tempo_score),
        ],
        key=lambda item: item[1],
    )[0]

    mean_view_quality = _safe_float(analysis["summary"].get("mean_view_quality"), 0.0)
    if mean_view_quality < calibration["tolerances"]["view_quality_min"]:
        score_float = min(score_float, calibration["caps"]["bad_view_max_score"])
        errors.append("Недостаточный ракурс")
        tips.append("Поставьте камеру в согласованный ракурс и оставьте всё тело в кадре.")
        caps_applied.append("bad_view")

    if min(primary_ratio, secondary_ratio, depth_ratio) < calibration["tolerances"]["range_ratio_low"] * 0.9:
        score_float = min(score_float, calibration["caps"]["severe_range_max_score"])
        errors.append("Недостаточная амплитуда")
        tips.append("Верните глубину и амплитуду ближе к эталонному повтору.")
        caps_applied.append("range")

    if posture_delta > calibration["tolerances"]["torso_tilt_deg"] * 1.15 or torso_curve_error > calibration["tolerances"]["curve_mae"] * 1.15:
        score_float = min(score_float, calibration["caps"]["severe_posture_max_score"])
        errors.append("Положение корпуса выходит за допуск")
        tips.append("Стабилизируйте корпус и удерживайте более близкий к эталону угол наклона.")
        caps_applied.append("posture")

    if asymmetry_delta > calibration["tolerances"]["asymmetry_pct"] * 1.15:
        score_float = min(score_float, calibration["caps"]["severe_asymmetry_max_score"])
        errors.append("Асимметрия выше допустимой")
        tips.append("Сведите к минимуму разницу между правой и левой стороной.")
        caps_applied.append("asymmetry")

    heel_lift_delta = max(
        0.0,
        _safe_float(analysis["summary"].get("p90_heel_lift"), 0.0)
        - _safe_float(reference_summary.get("p90_heel_lift"), 0.0),
    )
    if heel_lift_delta > calibration["tolerances"]["heel_lift_norm"]:
        score_float = min(score_float, calibration["caps"]["severe_heel_lift_max_score"])
        errors.append("Потеря опоры / отрыв пятки")
        tips.append("Сохраняйте опору и не допускайте заметного отрыва пятки от эталонной траектории.")
        caps_applied.append("heel_lift")

    if not tips:
        if lowest_bucket == "trajectory":
            tips.append("Сделайте повтор ближе к эталонной траектории по всей амплитуде.")
        elif lowest_bucket == "range":
            tips.append("Добавьте или сократите амплитуду до диапазона эталонного повтора.")
        elif lowest_bucket == "posture":
            tips.append("Стабилизируйте положение корпуса и не выходите из заданного угла.")
        elif lowest_bucket == "symmetry":
            tips.append("Выравняйте работу сторон и снимите лишнюю асимметрию.")
        elif lowest_bucket == "stability":
            tips.append("Сделайте движение плавнее, без лишних рывков и скачков.")
        else:
            tips.append("Старайтесь удерживать темп ближе к эталонному повтору.")

    rep_score = int(round(_clamp(score_float, 1.0, 100.0)))
    hint_codes, voice_feedback, rule_flags = _generated_hint_context(
        motion_family=str(reference_model.get("motion_family") or "squat_like"),
        rep_score=rep_score,
        caps_applied=caps_applied,
        lowest_bucket=lowest_bucket,
    )

    return {
        "rep_score": rep_score,
        "quality": _score_label(rep_score),
        "errors": list(dict.fromkeys(errors)),
        "tips": list(dict.fromkeys(tips))[:4],
        "metrics": {
            "primary_amplitude": round(_safe_float(analysis["summary"].get("primary_amplitude"), 0.0), 4),
            "secondary_amplitude": round(_safe_float(analysis["summary"].get("secondary_amplitude"), 0.0), 4),
            "depth_amplitude": round(_safe_float(analysis["summary"].get("depth_amplitude"), 0.0), 4),
            "primary_ratio": round(primary_ratio, 4),
            "secondary_ratio": round(secondary_ratio, 4),
            "depth_ratio": round(depth_ratio, 4),
            "p90_posture_tilt_deg": round(_safe_float(analysis["summary"].get("p90_posture_tilt_deg"), 0.0), 4),
            "mean_asymmetry": round(_safe_float(analysis["summary"].get("mean_asymmetry"), 0.0), 4),
            "p90_heel_lift": round(_safe_float(analysis["summary"].get("p90_heel_lift"), 0.0), 4),
            "mean_view_quality": round(mean_view_quality, 4),
            "smoothness_norm": round(_safe_float(analysis["summary"].get("smoothness_norm"), 0.0), 6),
            "duration_ms": round(_safe_float(analysis.get("duration_ms"), 0.0), 2),
        },
        "details": {
            "scores": {
                "trajectory": round(trajectory_score, 3),
                "range_of_motion": round(range_score, 3),
                "posture": round(posture_score, 3),
                "symmetry": round(symmetry_score, 3),
                "stability": round(stability_score, 3),
                "tempo": round(tempo_score, 3),
            },
            "curve_errors": {
                "primary": round(primary_curve_error, 5),
                "secondary": round(secondary_curve_error, 5),
                "depth": round(depth_curve_error, 5),
                "torso": round(torso_curve_error, 5),
            },
            "caps_applied": caps_applied,
            "hint_codes": hint_codes,
            "voice_feedback": voice_feedback,
            "rule_flags": rule_flags,
            "analysis": analysis["summary"],
            "calibration_profile": calibration,
        },
    }
