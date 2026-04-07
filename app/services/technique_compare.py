from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class CompareResult:
    rep_score: int
    quality: str
    errors: list[str]
    tips: list[str]
    metrics: dict[str, float]
    details: dict[str, Any]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _deadzone(value: float, deadzone: float) -> float:
    if value <= deadzone:
        return 0.0
    return (value - deadzone) / max(1.0 - deadzone, 1e-6)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * (pct / 100.0)
    left = int(position)
    right = min(left + 1, len(values) - 1)
    if left == right:
        return values[left]
    weight = position - left
    return values[left] * (1.0 - weight) + values[right] * weight


def _weighted_issue_penalty(
    code: str,
    title: str,
    severity: float,
    weight: float,
    *,
    deadzone: float = 0.0,
    power: float = 1.0,
) -> dict[str, float | str]:
    normalized = _clamp(severity, 0.0, 1.0)
    adjusted = _deadzone(normalized, deadzone)
    scaled = adjusted ** power if adjusted > 0 else 0.0
    penalty = float(weight) * scaled
    return {
        "code": code,
        "title": title,
        "severity": round(normalized, 4),
        "weight": round(float(weight), 2),
        "penalty": round(penalty, 4),
    }


def _fixed_issue_penalty(code: str, title: str, penalty: float) -> dict[str, float | str]:
    normalized_penalty = max(0.0, float(penalty))
    return {
        "code": code,
        "title": title,
        "severity": 1.0 if normalized_penalty > 0 else 0.0,
        "weight": round(normalized_penalty, 2),
        "penalty": round(normalized_penalty, 4),
    }


def _active_issue_penalties(items: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    return [item for item in items if float(item.get("penalty", 0.0)) > 0.05]


def _voice_feedback_payload(
    exercise: str,
    *,
    top_issue_code: str | None,
    hint_codes: list[str],
    errors: list[str],
) -> dict[str, str]:
    message_map = {
        "squat": {
            "heel_lift": "Не отрывайте пятки от пола.",
            "undersquat": "Добавьте глубину приседа.",
            "undersquat_severe": "Опуститесь заметно ниже и держите контроль.",
            "torso_forward": "Не заваливайте корпус вперёд.",
            "asymmetry": "Двигайтесь симметрично, без перекоса сторон.",
            "camera_side_view": "Повернитесь ровно боком к камере.",
            "good_rep": "Ты молодец, так держать.",
        },
        "pushup": {
            "partial_range": "Опуститесь ниже.",
            "body_line_break": "Держите корпус прямой линией.",
            "leg_line_break": "Не сгибайте ноги.",
            "asymmetry": "Работайте руками симметрично.",
            "camera_side_view": "Повернитесь боком к камере.",
            "excessive_depth_drop": "Не проваливайтесь внизу.",
            "good_rep": "Ты молодец, так держать.",
        },
    }
    priority_map = {
        "heel_lift": "high",
        "undersquat": "med",
        "undersquat_severe": "high",
        "torso_forward": "med",
        "asymmetry": "med",
        "camera_side_view": "low",
        "partial_range": "med",
        "body_line_break": "high",
        "leg_line_break": "med",
        "excessive_depth_drop": "med",
        "good_rep": "low",
    }

    exercise_map = message_map.get(exercise, {})
    ranked_codes = [code for code in [top_issue_code, *hint_codes] if code]
    for code in ranked_codes:
        if code in exercise_map:
            return {
                "code": code,
                "message": exercise_map[code],
                "priority": priority_map.get(code, "med"),
            }

    if errors:
        return {"code": "error", "message": errors[0], "priority": "med"}

    return {
        "code": "good_rep",
        "message": exercise_map.get("good_rep", "Чистый повтор."),
        "priority": "low",
    }


def _select_voice_issue_code(
    hint_codes: list[str],
    top_issue_code: str | None,
) -> str | None:
    explicit_issue_codes = [
        str(code)
        for code in hint_codes
        if code and str(code) != "good_rep"
    ]
    if explicit_issue_codes:
        return explicit_issue_codes[0]
    if "good_rep" in hint_codes:
        return "good_rep"
    return top_issue_code


def _score_label(score: int) -> str:
    if score >= 85:
        return "Отлично"
    if score >= 60:
        return "Нормально"
    return "Нужно улучшить"


def _safe_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_frames(frame_metrics: list[dict[str, Any]]) -> list[dict[str, float]]:
    normalized: list[dict[str, float]] = []
    for item in frame_metrics:
        normalized.append(
            {
                "primary_angle": _safe_float(item.get("primary_angle"), 180.0),
                "secondary_angle": _safe_float(item.get("secondary_angle"), 180.0),
                "depth_norm": _safe_float(item.get("depth_norm"), 0.0),
                "torso_angle": _safe_float(item.get("torso_angle"), 0.0),
                "asymmetry": _safe_float(item.get("asymmetry"), 0.0),
                "hip_asymmetry": _safe_float(item.get("hip_asymmetry"), 0.0),
                "side_view_score": _safe_float(item.get("side_view_score"), 0.0),
                "heel_lift_norm": _safe_float(item.get("heel_lift_norm"), 0.0),
                "leg_angle": _safe_float(item.get("leg_angle"), 180.0),
            }
        )
    return normalized


def compare_squat_rep(frame_metrics: list[dict[str, Any]]) -> CompareResult:
    frames = _normalize_frames(frame_metrics)
    if len(frames) < 4:
        return CompareResult(
            rep_score=0,
            quality="Нужно улучшить",
            errors=["Недостаточно данных по повтору."],
            tips=["Выполните полный повтор (UP→DOWN→UP)."],
            metrics={},
            details={"reason": "insufficient_frames"},
        )

    primary = [row["primary_angle"] for row in frames]
    secondary = [row["secondary_angle"] for row in frames]
    depth = [row["depth_norm"] for row in frames]
    torso = [row["torso_angle"] for row in frames]
    asym = [row["asymmetry"] for row in frames]
    hip_asym = [row["hip_asymmetry"] for row in frames]
    heel = [max(0.0, row["heel_lift_norm"]) for row in frames]
    side = [row["side_view_score"] for row in frames]

    head = max(3, len(frames) // 8)
    # Baseline from the top position (not strictly from first frames) to avoid drift between reps.
    baseline_depth = mean(sorted(depth, reverse=True)[:head])
    baseline_heel = mean(sorted(heel)[:head])

    depth_delta = [max(0.0, baseline_depth - value) for value in depth]
    heel_delta = [max(0.0, value - baseline_heel) for value in heel]
    heel_delta_sorted = sorted(heel_delta)
    heel_abs_sorted = sorted(heel)

    min_knee_angle = min(primary)
    min_hip_angle = min(secondary)
    max_depth_delta = max(depth_delta)
    max_torso_forward = max(torso)
    mean_side_view = mean(side)
    mean_knee_asym = mean(asym)
    mean_hip_asym = mean(hip_asym)
    p90_heel_lift = _percentile(heel_delta_sorted, 90)
    p90_heel_abs = _percentile(heel_abs_sorted, 90)
    mean_heel_lift = mean(heel_delta)
    mean_heel_abs = mean(heel)
    heel_spike_ratio = (
        sum(1 for value in heel_delta if value >= 0.055) / len(heel_delta)
        if heel_delta
        else 0.0
    )
    heel_abs_spike_ratio = (
        sum(1 for value in heel if value >= 0.08) / len(heel)
        if heel
        else 0.0
    )

    ref_min_knee_angle = 95.0
    ref_min_hip_angle = 105.0
    ref_depth_delta = 0.24
    ref_torso_forward = 26.0
    ref_knee_asym = 4.0
    ref_hip_asym = 4.0

    ref_knee_flex = max(1e-6, 180.0 - ref_min_knee_angle)
    rep_knee_flex = max(0.0, 180.0 - min_knee_angle)
    knee_ratio = rep_knee_flex / ref_knee_flex

    ref_hip_flex = max(1e-6, 180.0 - ref_min_hip_angle)
    rep_hip_flex = max(0.0, 180.0 - min_hip_angle)
    hip_ratio = rep_hip_flex / ref_hip_flex

    depth_ratio = max_depth_delta / max(ref_depth_delta, 1e-6)
    torso_excess = max(0.0, max_torso_forward - ref_torso_forward)
    asym_excess = max(mean_knee_asym - ref_knee_asym, mean_hip_asym - ref_hip_asym)

    # score = 100 - penalties + boosts
    base_score = 100.0

    depth_deficit = _clamp((0.92 - depth_ratio) / 0.92, 0.0, 1.0)
    knee_deficit = _clamp((0.93 - knee_ratio) / 0.93, 0.0, 1.0)
    over_depth_excess = _clamp((depth_ratio - 1.20) / 1.20, 0.0, 1.0)
    over_knee_excess = _clamp((knee_ratio - 1.20) / 1.20, 0.0, 1.0)
    torso_deficit = _clamp(torso_excess / 10.0, 0.0, 1.0)
    asym_deficit = _clamp(asym_excess / 12.0, 0.0, 1.0)
    side_deficit = _clamp((0.68 - mean_side_view) / 0.68, 0.0, 1.0)
    heel_deficit = _clamp((p90_heel_lift - 0.03) / 0.03, 0.0, 1.0)

    issue_penalties = [
        _weighted_issue_penalty(
            "depth_range",
            "Отклонение рабочей глубины",
            depth_deficit,
            72.0,
            deadzone=0.02,
        ),
        _weighted_issue_penalty(
            "over_depth",
            "Провал глубже эталона",
            over_depth_excess,
            16.0,
            deadzone=0.05,
        ),
        _weighted_issue_penalty(
            "knee_depth_control",
            "Отклонение по работе колена",
            knee_deficit,
            62.0,
            deadzone=0.02,
        ),
        _weighted_issue_penalty(
            "over_knee_flex",
            "Избыточное сгибание колена",
            over_knee_excess,
            12.0,
            deadzone=0.05,
        ),
        _weighted_issue_penalty(
            "torso_forward",
            "Избыточный наклон корпуса",
            torso_deficit,
            22.0,
            deadzone=0.06,
        ),
        _weighted_issue_penalty(
            "asymmetry",
            "Асимметрия сторон",
            asym_deficit,
            18.0,
            deadzone=0.05,
        ),
        _weighted_issue_penalty(
            "camera_side_view",
            "Недостаточный боковой ракурс",
            side_deficit,
            20.0,
            deadzone=0.04,
        ),
        _weighted_issue_penalty(
            "heel_lift",
            "Отрыв пяток",
            heel_deficit,
            8.0,
            deadzone=0.08,
        ),
    ]

    poor_depth = depth_ratio < 0.84 or knee_ratio < 0.90
    undersquat = depth_ratio < 0.78 or knee_ratio < 0.88
    undersquat_severe = depth_ratio < 0.62 or knee_ratio < 0.74 or min_knee_angle > 124.0
    undersquat_depth_severity = _clamp((0.78 - depth_ratio) / 0.78, 0.0, 1.0)
    undersquat_knee_severity = _clamp((0.88 - knee_ratio) / 0.88, 0.0, 1.0)
    issue_penalties.extend(
        [
            _weighted_issue_penalty(
                "undersquat_depth",
                "Недостаточная глубина приседа",
                undersquat_depth_severity,
                34.0,
                deadzone=0.03,
            ),
            _weighted_issue_penalty(
                "undersquat_knee",
                "Недоработка колена по глубине",
                undersquat_knee_severity,
                28.0,
                deadzone=0.03,
            ),
        ]
    )
    undersquat_penalty = sum(
        float(item["penalty"])
        for item in issue_penalties
        if item["code"] in {"undersquat_depth", "undersquat_knee"}
    )
    if undersquat:
        issue_penalties.append(
            _fixed_issue_penalty(
                "undersquat",
                "Недостаточная глубина приседа",
                15.0,
            )
        )
        undersquat_penalty += 15.0
    if undersquat_severe:
        issue_penalties.append(
            _fixed_issue_penalty(
                "undersquat_severe",
                "Критический недосед",
                22.0,
            )
        )
        undersquat_penalty += 22.0

    penalty_parts = {
        "depth": round(
            sum(
                float(item["penalty"])
                for item in issue_penalties
                if item["code"] in {"depth_range", "over_depth"}
            ),
            2,
        ),
        "knee": round(
            sum(
                float(item["penalty"])
                for item in issue_penalties
                if item["code"] in {"knee_depth_control", "over_knee_flex"}
            ),
            2,
        ),
        "undersquat": round(undersquat_penalty, 2),
        "torso": round(
            sum(
                float(item["penalty"])
                for item in issue_penalties
                if item["code"] == "torso_forward"
            ),
            2,
        ),
        "asymmetry": round(
            sum(
                float(item["penalty"])
                for item in issue_penalties
                if item["code"] == "asymmetry"
            ),
            2,
        ),
        "side_view": round(
            sum(
                float(item["penalty"])
                for item in issue_penalties
                if item["code"] == "camera_side_view"
            ),
            2,
        ),
        "heel": round(
            sum(
                float(item["penalty"])
                for item in issue_penalties
                if item["code"] == "heel_lift"
            ),
            2,
        ),
    }
    penalty_total = sum(float(item["penalty"]) for item in issue_penalties)

    heel_fail_delta = (
        p90_heel_lift >= 0.09
        and mean_heel_lift >= 0.03
        and heel_spike_ratio >= 0.35
    )
    heel_fail_abs = (
        p90_heel_abs >= 0.14
        and mean_heel_abs >= 0.09
        and heel_abs_spike_ratio >= 0.45
        and p90_heel_lift >= 0.05
        and mean_heel_lift >= 0.02
    )
    heel_fail = (
        (heel_fail_delta or heel_fail_abs)
        and mean_side_view >= 0.64
        and max_depth_delta >= 0.10
    )

    good_pose = (
        0.90 <= depth_ratio <= 1.12
        and 0.90 <= knee_ratio <= 1.15
        and torso_excess <= 6.0
        and asym_excess <= 9.0
        and mean_side_view >= 0.68
    )
    excellent_pose = (
        0.95 <= depth_ratio <= 1.06
        and 0.95 <= knee_ratio <= 1.10
        and torso_excess <= 3.5
        and asym_excess <= 6.0
        and mean_side_view >= 0.72
    )

    boost_applied = "none"
    boost_value = 0.0
    if not heel_fail and not undersquat:
        if excellent_pose:
            boost_applied = "excellent_pose"
            boost_value = 10.0
        elif good_pose:
            boost_applied = "good_pose"
            boost_value = 6.0

    rep_score_float = _clamp(base_score - penalty_total + boost_value, 8.0, 100.0)
    rep_score = int(round(rep_score_float))

    poor_depth_cap_65 = False
    undersquat_cap_40 = False
    undersquat_severe_cap_30 = False
    if undersquat_severe and not heel_fail:
        rep_score = min(rep_score, 30)
        undersquat_severe_cap_30 = True
    elif undersquat and not heel_fail:
        rep_score = min(rep_score, 40)
        undersquat_cap_40 = True
    elif poor_depth and not heel_fail:
        rep_score = min(rep_score, 65)
        poor_depth_cap_65 = True

    if not heel_fail and not poor_depth:
        if excellent_pose:
            rep_score = max(rep_score, 92)
        elif good_pose:
            rep_score = max(rep_score, 84)

    if heel_fail:
        rep_score = 1
        boost_applied = "none"

    errors: list[str] = []
    tips: list[str] = []
    hint_codes: list[str] = []

    if mean_side_view < 0.62:
        errors.append("Недостаточно боковой ракурс")
        tips.append("Повернитесь к камере боком и держите камеру на уровне таза.")
        hint_codes.append("camera_side_view")

    if heel_fail:
        errors.append("Отрыв пяток (критично)")
        tips.append("Пятки на пол, уменьшите глубину на 10-15% и сохраняйте темп.")
        hint_codes.append("heel_lift")

    if (undersquat or poor_depth) and not heel_fail:
        errors.append("Недостаточная глубина приседа")
        tips.append("Недосед: добавьте глубину до рабочего уровня и фиксируйте низ на 0.3-0.5 сек.")
        hint_codes.append("undersquat")

    if torso_excess > 6.0:
        errors.append("Избыточный наклон корпуса")
        tips.append("Корпус: грудь выше, темп вниз медленнее, вес держите в середине стопы.")
        hint_codes.append("torso_forward")

    if asym_excess > 8.0:
        errors.append("Асимметрия сторон")
        tips.append("Держите колени и таз симметрично: одинаковая скорость и глубина с обеих сторон.")
        hint_codes.append("asymmetry")

    if not errors:
        tips.append("Повтор чистый: держите тот же темп и такую же глубину.")
        hint_codes.append("good_rep")

    # Deduplicate while preserving order.
    hint_codes = list(dict.fromkeys(hint_codes))
    tips = list(dict.fromkeys(tips))
    active_issue_penalties = _active_issue_penalties(issue_penalties)
    top_issue = max(active_issue_penalties, key=lambda item: float(item["penalty"]), default=None)
    top_issue_code = _select_voice_issue_code(
        hint_codes,
        "heel_lift" if heel_fail else (str(top_issue["code"]) if top_issue else None),
    )
    voice_feedback = _voice_feedback_payload(
        "squat",
        top_issue_code=top_issue_code,
        hint_codes=hint_codes,
        errors=errors,
    )

    metrics = {
        "min_knee_angle": round(min_knee_angle, 3),
        "min_hip_angle": round(min_hip_angle, 3),
        "max_depth_delta": round(max_depth_delta, 4),
        "depth_ratio": round(depth_ratio, 4),
        "knee_ratio": round(knee_ratio, 4),
        "hip_ratio": round(hip_ratio, 4),
        "max_torso_forward": round(max_torso_forward, 3),
        "p90_heel_lift": round(p90_heel_lift, 4),
        "p90_heel_abs": round(p90_heel_abs, 4),
        "mean_heel_lift": round(mean_heel_lift, 4),
        "mean_heel_abs": round(mean_heel_abs, 4),
        "mean_side_view_score": round(mean_side_view, 4),
    }

    details = {
        "score_base": round(base_score, 2),
        "penalty": round(penalty_total, 4),
        "heel_fail": heel_fail,
        "heel_spike_ratio": round(heel_spike_ratio, 4),
        "heel_abs_spike_ratio": round(heel_abs_spike_ratio, 4),
        "undersquat": undersquat,
        "undersquat_severe": undersquat_severe,
        "poor_depth": poor_depth,
        "good_pose": good_pose,
        "excellent_pose": excellent_pose,
        "hint_codes": hint_codes,
        "voice_feedback": voice_feedback,
        "rule_flags": {
            "heel_fail": heel_fail,
            "undersquat": undersquat,
            "undersquat_severe": undersquat_severe,
            "good_pose": good_pose,
            "excellent_pose": excellent_pose,
        },
        "score_breakdown": {
            "base_score": round(base_score, 2),
            "penalty_total": round(penalty_total, 2),
            "issue_penalties": active_issue_penalties,
            "penalty_parts": penalty_parts,
            "boost_applied": boost_applied,
            "boost_value": round(boost_value, 2),
            "hard_caps": {
                "heel_fail_to_0": False,
                "heel_fail_to_1": heel_fail,
                "poor_depth_cap_65": poor_depth_cap_65,
                "undersquat_cap_40": undersquat_cap_40,
                "undersquat_severe_cap_30": undersquat_severe_cap_30,
            },
            "rule_flags": {
                "heel_fail": heel_fail,
                "poor_depth": poor_depth,
                "undersquat": undersquat,
                "undersquat_severe": undersquat_severe,
                "good_pose": good_pose,
                "excellent_pose": excellent_pose,
            },
            "top_issue_code": top_issue_code,
            "final_score": rep_score,
        },
        "config": {
            "torso_reference_deg": ref_torso_forward,
            "heel_lift_delta_fail_threshold": 0.09,
            "heel_lift_delta_mean_threshold": 0.03,
            "heel_lift_delta_spike_ratio_threshold": 0.35,
            "heel_lift_abs_fail_threshold": 0.14,
            "heel_lift_abs_mean_threshold": 0.09,
            "heel_lift_abs_spike_ratio_threshold": 0.45,
            "heel_lift_side_view_min_threshold": 0.64,
            "heel_lift_min_depth_delta": 0.10,
            "poor_depth_threshold_depth_ratio": 0.84,
            "poor_depth_threshold_knee_ratio": 0.90,
            "undersquat_depth_threshold": 0.78,
            "undersquat_knee_threshold": 0.88,
            "undersquat_severe_depth_threshold": 0.62,
            "undersquat_severe_knee_ratio_threshold": 0.74,
            "undersquat_severe_knee_angle_threshold": 124.0,
        },
    }

    return CompareResult(
        rep_score=rep_score,
        quality=_score_label(rep_score),
        errors=errors,
        tips=tips[:5],
        metrics=metrics,
        details=details,
    )


def compare_pushup_rep(frame_metrics: list[dict[str, Any]]) -> CompareResult:
    frames = _normalize_frames(frame_metrics)
    if len(frames) < 4:
        return CompareResult(
            rep_score=0,
            quality="Нужно улучшить",
            errors=["Недостаточно данных по повтору."],
            tips=["Выполните полный повтор (UP→DOWN→UP)."],
            metrics={},
            details={"reason": "insufficient_frames"},
        )

    elbow = [row["primary_angle"] for row in frames]
    body = [row["secondary_angle"] for row in frames]
    chest = [row["depth_norm"] for row in frames]
    body_bend = [row["torso_angle"] for row in frames]
    elbow_asym = [row["asymmetry"] for row in frames]
    body_asym = [row["hip_asymmetry"] for row in frames]
    leg = [row["leg_angle"] for row in frames]
    side = [row["side_view_score"] for row in frames]

    head = max(3, len(frames) // 8)
    baseline_chest = mean(chest[:head])
    depth_delta = [max(0.0, baseline_chest - value) for value in chest]
    depth_sorted = sorted(depth_delta)

    min_elbow_angle = min(elbow)
    min_leg_knee_angle = min(leg)
    p90_depth_delta = _percentile(depth_sorted, 90)
    max_depth_delta = max(depth_delta)
    p90_body_bend = _percentile(sorted(body_bend), 90)
    max_body_bend = max(body_bend)
    mean_body_bend = mean(body_bend)
    mean_elbow_asym = mean(elbow_asym)
    mean_body_asym = mean(body_asym)
    mean_side_view = mean(side)

    ref_min_elbow = 86.0
    ref_p90_depth = 0.20
    ref_max_depth = 0.22
    ref_p90_body_bend = 9.0
    ref_mean_elbow_asym = 3.5
    ref_mean_body_asym = 3.5

    ref_flex = max(1e-6, 180.0 - ref_min_elbow)
    rep_flex = max(0.0, 180.0 - min_elbow_angle)
    elbow_ratio = rep_flex / ref_flex

    target_depth = max(ref_p90_depth, ref_max_depth * 0.85, 1e-6)
    rep_depth = max(p90_depth_delta, max_depth_delta * 0.85)
    depth_ratio_raw = rep_depth / target_depth
    depth_ratio = max(depth_ratio_raw, elbow_ratio * 1.0)

    body_excess = max(0.0, p90_body_bend - ref_p90_body_bend - 1.5)
    asym_excess = max(
        0.0,
        mean_elbow_asym - ref_mean_elbow_asym,
        mean_body_asym - ref_mean_body_asym,
    )

    distance = (
        0.88 * ((elbow_ratio - 1.0) ** 2)
        + 0.12 * ((depth_ratio - 1.0) ** 2)
    ) ** 0.5

    # Базовые коэффициенты взяты из старого pushup-алгоритма и чуть ужесточены,
    # чтобы убрать завышение score в веб-версии.
    score_midpoint = 1.0
    score_curve = 1.14
    score_base = int(round(100.0 / (1.0 + (distance / max(score_midpoint, 1e-6)) ** score_curve)))
    score_base = max(8, min(100, score_base))

    depth_deficit = _clamp((0.68 - depth_ratio) / 0.68, 0.0, 1.0)
    over_depth_excess = _clamp((depth_ratio_raw - 1.18) / 1.18, 0.0, 1.0)
    elbow_deficit = _clamp((0.80 - elbow_ratio) / 0.80, 0.0, 1.0)
    body_deficit = _clamp(body_excess / 14.0, 0.0, 1.0)
    asym_deficit = _clamp(asym_excess / 10.0, 0.0, 1.0)
    leg_deficit = _clamp((138.0 - min_leg_knee_angle) / max(138.0 - 112.0, 1e-6), 0.0, 1.0)

    issue_penalties = [
        _weighted_issue_penalty(
            "partial_range",
            "Недостаточная глубина",
            depth_deficit,
            12.0,
            deadzone=0.2,
        ),
        _weighted_issue_penalty(
            "excessive_depth_drop",
            "Чрезмерный провал",
            over_depth_excess,
            14.0,
            deadzone=0.2,
        ),
        _weighted_issue_penalty(
            "elbow_depth_control",
            "Отклонение по паттерну локтя",
            elbow_deficit,
            16.0,
            deadzone=0.2,
        ),
        _weighted_issue_penalty(
            "leg_line_break",
            "Сильное сгибание ног",
            leg_deficit,
            9.0,
            deadzone=0.2,
        ),
        _weighted_issue_penalty(
            "body_line_break",
            "Ломается линия корпуса",
            body_deficit,
            12.0,
            deadzone=0.18,
        ),
        _weighted_issue_penalty(
            "asymmetry",
            "Асимметрия рук",
            asym_deficit,
            9.0,
            deadzone=0.2,
        ),
    ]

    if min_leg_knee_angle <= 112.0:
        issue_penalties.append(
            _fixed_issue_penalty(
                "leg_line_break_fail",
                "Критическое сгибание ног",
                4.0,
            )
        )

    distance_penalty = max(0.0, 100.0 - score_base)
    technique_penalty = sum(float(item["penalty"]) for item in issue_penalties)
    quality_bonus = 4.0

    if distance <= 0.03 and technique_penalty <= 2.0:
        rep_score = 100
    else:
        rep_score = int(
            round(
                _clamp(
                    100.0 - distance_penalty - technique_penalty + quality_bonus,
                    0.0,
                    100.0,
                )
            )
        )

    errors: list[str] = []
    tips: list[str] = []
    hint_codes: list[str] = []

    side_ok = mean_side_view >= 0.6
    depth_gate = 1.0 - 0.32
    elbow_gate = 1.0 - 0.26

    if not side_ok:
        errors.append("Недостаточно боковой ракурс")
        tips.append("Повернитесь боком к камере, чтобы точнее считать глубину и углы локтя.")
        hint_codes.append("camera_side_view")
    elif depth_ratio < depth_gate and elbow_ratio < elbow_gate:
        errors.append("Недостаточная глубина")
        tips.append("Опускайтесь ниже, контролируя локти и без провала корпуса.")
        hint_codes.append("partial_range")

    if p90_body_bend - ref_p90_body_bend > 14.0:
        errors.append("Ломается линия корпуса")
        tips.append("Держите тело ровной линией от плеч до голеностопа.")
        hint_codes.append("body_line_break")

    if asym_excess > 8.0:
        errors.append("Асимметрия рук")
        tips.append("Старайтесь равномерно нагружать обе стороны и держать локти симметрично.")
        hint_codes.append("asymmetry")

    if min_leg_knee_angle < 140.0:
        errors.append("Сильное сгибание ног")
        tips.append("Удерживайте ноги более прямыми и корпус стабильным.")
        hint_codes.append("leg_line_break")

    if depth_ratio_raw > 1.2:
        errors.append("Чрезмерный провал")
        tips.append("Избегайте провала в нижней точке, сохраняйте контроль амплитуды.")
        hint_codes.append("excessive_depth_drop")

    if not tips:
        tips.append("Повтор близок к эталону: сохраняйте текущий контроль движения.")
        hint_codes.append("good_rep")

    hint_codes = list(dict.fromkeys(hint_codes))
    active_issue_penalties = _active_issue_penalties(issue_penalties)
    top_issue = max(active_issue_penalties, key=lambda item: float(item["penalty"]), default=None)
    top_issue_code = _select_voice_issue_code(
        hint_codes,
        str(top_issue["code"]) if top_issue else None,
    )
    voice_feedback = _voice_feedback_payload(
        "pushup",
        top_issue_code=top_issue_code,
        hint_codes=hint_codes,
        errors=errors,
    )

    metrics = {
        "min_elbow_angle": round(min_elbow_angle, 3),
        "min_leg_knee_angle": round(min_leg_knee_angle, 3),
        "p90_depth_delta": round(p90_depth_delta, 4),
        "max_depth_delta": round(max_depth_delta, 4),
        "depth_ratio": round(depth_ratio, 4),
        "depth_ratio_raw": round(depth_ratio_raw, 4),
        "elbow_ratio": round(elbow_ratio, 4),
        "p90_body_bend": round(p90_body_bend, 3),
        "mean_side_view_score": round(mean_side_view, 4),
    }

    details = {
        "distance": round(distance, 6),
        "score_base": score_base,
        "penalty": round(distance_penalty + technique_penalty, 4),
        "hint_codes": hint_codes,
        "voice_feedback": voice_feedback,
        "rule_flags": {
            "body_fail": p90_body_bend - ref_p90_body_bend > 14.0,
            "poor_depth": depth_ratio < depth_gate and elbow_ratio < elbow_gate,
            "leg_line_break": min_leg_knee_angle < 140.0,
            "good_pose": distance <= 0.05 and technique_penalty <= 4.0,
            "excellent_pose": distance <= 0.03 and technique_penalty <= 2.0,
        },
        "score_breakdown": {
            "base_score": 100.0,
            "distance_penalty": round(distance_penalty, 2),
            "technique_penalty": round(technique_penalty, 2),
            "issue_penalties": active_issue_penalties,
            "quality_bonus": round(quality_bonus, 2),
            "top_issue_code": top_issue_code,
            "final_score": rep_score,
        },
        "config": {
            "depth_ratio_gate": 0.68,
            "over_depth_ratio_gate": 1.18,
            "elbow_ratio_gate": 0.80,
            "leg_knee_min_angle_deg": 138.0,
            "leg_knee_fail_angle_deg": 112.0,
            "score_midpoint": score_midpoint,
            "score_curve": score_curve,
        },
    }

    return CompareResult(
        rep_score=rep_score,
        quality=_score_label(rep_score),
        errors=errors,
        tips=tips[:5],
        metrics=metrics,
        details=details,
    )
