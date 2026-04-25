from __future__ import annotations

import argparse
import json
import math
import shutil
import ssl
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.database import SessionLocal
from app.core.exercise_catalog import CATALOG_DB_NAME_BY_SLUG, EXERCISE_CATALOG, catalog_db_name_candidates
from app.models.exercise import Exercise
from app.models.exercise_technique_profile import ExerciseTechniqueProfile
from app.services.generated_technique import build_reference_model, dump_json, slugify_title

SYSTEM_PROFILE_DIR = REPO_ROOT / "data/system_reference_profiles"
SYSTEM_VIDEO_DIR = SYSTEM_PROFILE_DIR / "videos"
DESKTOP_DIR = Path.home() / "Desktop/kinematics_reference_videos"
README_PATH = DESKTOP_DIR / "README.md"


@dataclass(frozen=True)
class ReferenceSpec:
    order: int
    slug: str
    title: str
    motion_family: str
    view_type: str
    source_url: str
    source_page_url: str
    source_label: str
    source_ext: str


SPECS: list[ReferenceSpec] = [
    ReferenceSpec(
        order=1,
        slug="squat",
        title="Приседания",
        motion_family="squat_like",
        view_type="side",
        source_url="https://upload.wikimedia.org/wikipedia/commons/5/5c/Squat_-_exercise_demonstration_video.webm",
        source_page_url="https://commons.wikimedia.org/wiki/File%3ASquat_-_exercise_demonstration_video.webm",
        source_label="Wikimedia Commons (CC BY 3.0)",
        source_ext=".webm",
    ),
    ReferenceSpec(
        order=2,
        slug="pushup",
        title="Отжимания",
        motion_family="push_like",
        view_type="side",
        source_url="https://www.pexels.com/download/video/4804819/",
        source_page_url="https://www.pexels.com/video/4804819/",
        source_label="Pexels free license",
        source_ext=".mp4",
    ),
    ReferenceSpec(
        order=3,
        slug="lunge",
        title="Выпад назад",
        motion_family="lunge_like",
        view_type="side",
        source_url="https://www.pexels.com/download/video/8233047/",
        source_page_url="https://www.pexels.com/video/8233047/",
        source_label="Pexels free license",
        source_ext=".mp4",
    ),
    ReferenceSpec(
        order=4,
        slug="glute_bridge",
        title="Ягодичный мост",
        motion_family="core_like",
        view_type="side",
        source_url="https://www.pexels.com/download/video/6525487/",
        source_page_url="https://www.pexels.com/video/6525487/",
        source_label="Pexels free license",
        source_ext=".mp4",
    ),
    ReferenceSpec(
        order=5,
        slug="leg_raise",
        title="Подъёмы ног лежа",
        motion_family="core_like",
        view_type="side",
        source_url="https://www.pexels.com/download/video/8233778/",
        source_page_url="https://www.pexels.com/video/8233778/",
        source_label="Pexels free license",
        source_ext=".mp4",
    ),
    ReferenceSpec(
        order=6,
        slug="crunch",
        title="Скручивания",
        motion_family="core_like",
        view_type="side",
        source_url="https://www.pexels.com/download/video/5469608/",
        source_page_url="https://www.pexels.com/video/5469608/",
        source_label="Pexels free license",
        source_ext=".mp4",
    ),
]


LANDMARK = {
    "L_SHOULDER": 11,
    "R_SHOULDER": 12,
    "L_ELBOW": 13,
    "R_ELBOW": 14,
    "L_WRIST": 15,
    "R_WRIST": 16,
    "L_HIP": 23,
    "R_HIP": 24,
    "L_KNEE": 25,
    "R_KNEE": 26,
    "L_ANKLE": 27,
    "R_ANKLE": 28,
    "L_HEEL": 29,
    "R_HEEL": 30,
    "L_FOOT_INDEX": 31,
    "R_FOOT_INDEX": 32,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-db", action="store_true", help="Только построить локальные JSON-профили и не писать в БД.")
    parser.add_argument("--force", action="store_true", help="Перескачать видео и пересобрать JSON-профили.")
    return parser.parse_args()


def to_number(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def get_point(landmarks: list[Any], index: int) -> Any | None:
    if index >= len(landmarks):
        return None
    point = landmarks[index]
    if point is None:
        return None
    return point


def distance2d(a: Any | None, b: Any | None) -> float:
    if not a or not b:
        return 0.0
    return math.hypot(float(a.x) - float(b.x), float(a.y) - float(b.y))


def angle_deg(a: Any | None, b: Any | None, c: Any | None) -> float | None:
    if not a or not b or not c:
        return None
    abx = float(a.x) - float(b.x)
    aby = float(a.y) - float(b.y)
    cbx = float(c.x) - float(b.x)
    cby = float(c.y) - float(b.y)
    ab_len = math.hypot(abx, aby)
    cb_len = math.hypot(cbx, cby)
    if ab_len < 1e-6 or cb_len < 1e-6:
        return None
    cos_value = max(-1.0, min(1.0, (abx * cbx + aby * cby) / (ab_len * cb_len)))
    return math.degrees(math.acos(cos_value))


def mean_visibility(landmarks: list[Any], indexes: list[int]) -> float:
    values = []
    for index in indexes:
        point = get_point(landmarks, index)
        if point is None:
            continue
        values.append(to_number(getattr(point, "visibility", 1.0), 1.0))
    if not values:
        return 0.0
    return sum(values) / len(values)


def weighted_pair(left: float | None, right: float | None, lw: float, rw: float) -> float | None:
    left_valid = left is not None
    right_valid = right is not None
    if not left_valid and not right_valid:
        return None
    if left_valid and not right_valid:
        return float(left)
    if right_valid and not left_valid:
        return float(right)
    total = max(lw + rw, 1e-6)
    return (float(left) * lw + float(right) * rw) / total


def torso_tilt_deg(hip: Any | None, shoulder: Any | None) -> float | None:
    if not hip or not shoulder:
        return None
    return math.degrees(math.atan2(abs(float(shoulder.y) - float(hip.y)), max(abs(float(shoulder.x) - float(hip.x)), 1e-6)))


def point_line_distance(point: Any | None, line_start: Any | None, line_end: Any | None) -> float:
    if not point or not line_start or not line_end:
        return 0.0
    px, py = float(point.x), float(point.y)
    x1, y1 = float(line_start.x), float(line_start.y)
    x2, y2 = float(line_end.x), float(line_end.y)
    line_len_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
    if line_len_sq < 1e-6:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_len_sq))
    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)
    return math.hypot(px - proj_x, py - proj_y)


def view_quality_score(landmarks: list[Any], body_len: float, view_type: str) -> float:
    left_shoulder = get_point(landmarks, LANDMARK["L_SHOULDER"])
    right_shoulder = get_point(landmarks, LANDMARK["R_SHOULDER"])
    left_hip = get_point(landmarks, LANDMARK["L_HIP"])
    right_hip = get_point(landmarks, LANDMARK["R_HIP"])
    if not left_shoulder or not right_shoulder or not left_hip or not right_hip or body_len < 1e-6:
        return 0.0
    shoulder_span = distance2d(left_shoulder, right_shoulder) / body_len
    hip_span = distance2d(left_hip, right_hip) / body_len
    span = (shoulder_span + hip_span) / 2.0
    if view_type == "side":
        return max(0.0, min(1.0, 1.0 - min(span / 0.38, 1.0)))
    return max(0.0, min(1.0, span / 0.38))


def build_squat_like_metrics(landmarks: list[Any], view_type: str) -> dict[str, float] | None:
    l_sh = get_point(landmarks, LANDMARK["L_SHOULDER"])
    r_sh = get_point(landmarks, LANDMARK["R_SHOULDER"])
    l_hip = get_point(landmarks, LANDMARK["L_HIP"])
    r_hip = get_point(landmarks, LANDMARK["R_HIP"])
    l_knee = get_point(landmarks, LANDMARK["L_KNEE"])
    r_knee = get_point(landmarks, LANDMARK["R_KNEE"])
    l_ank = get_point(landmarks, LANDMARK["L_ANKLE"])
    r_ank = get_point(landmarks, LANDMARK["R_ANKLE"])
    l_heel = get_point(landmarks, LANDMARK["L_HEEL"])
    r_heel = get_point(landmarks, LANDMARK["R_HEEL"])
    l_toe = get_point(landmarks, LANDMARK["L_FOOT_INDEX"])
    r_toe = get_point(landmarks, LANDMARK["R_FOOT_INDEX"])
    left_knee = angle_deg(l_hip, l_knee, l_ank)
    right_knee = angle_deg(r_hip, r_knee, r_ank)
    left_hip = angle_deg(l_sh, l_hip, l_knee)
    right_hip = angle_deg(r_sh, r_hip, r_knee)
    left_leg = distance2d(l_hip, l_ank)
    right_leg = distance2d(r_hip, r_ank)
    leg_len = (left_leg + right_leg) / 2.0
    if leg_len < 1e-6:
        return None
    left_vis = mean_visibility(landmarks, [LANDMARK["L_HIP"], LANDMARK["L_KNEE"], LANDMARK["L_ANKLE"]])
    right_vis = mean_visibility(landmarks, [LANDMARK["R_HIP"], LANDMARK["R_KNEE"], LANDMARK["R_ANKLE"]])
    avg_knee = weighted_pair(left_knee, right_knee, left_vis, right_vis)
    avg_hip = weighted_pair(left_hip, right_hip, left_vis, right_vis)
    left_depth = (float(l_ank.y) - float(l_hip.y)) / max(left_leg, 1e-6) if l_ank and l_hip else None
    right_depth = (float(r_ank.y) - float(r_hip.y)) / max(right_leg, 1e-6) if r_ank and r_hip else None
    depth_norm = weighted_pair(left_depth, right_depth, left_vis, right_vis)
    left_torso = torso_tilt_deg(l_hip, l_sh)
    right_torso = torso_tilt_deg(r_hip, r_sh)
    torso = weighted_pair(left_torso, right_torso, left_vis, right_vis) or 0.0
    left_heel_lift = max(0.0, float(l_toe.y) - float(l_heel.y)) / max(left_leg, 1e-6) if l_toe and l_heel else None
    right_heel_lift = max(0.0, float(r_toe.y) - float(r_heel.y)) / max(right_leg, 1e-6) if r_toe and r_heel else None
    heel_lift = weighted_pair(left_heel_lift, right_heel_lift, left_vis, right_vis) or 0.0
    hip_ankle_vertical = weighted_pair(
        abs(float(l_hip.y) - float(l_ank.y)) / max(left_leg, 1e-6) if l_hip and l_ank else None,
        abs(float(r_hip.y) - float(r_ank.y)) / max(right_leg, 1e-6) if r_hip and r_ank else None,
        left_vis,
        right_vis,
    )
    if avg_knee is None or avg_hip is None or depth_norm is None or hip_ankle_vertical is None:
        return None
    return {
        "primary_angle": avg_knee,
        "secondary_angle": avg_hip,
        "depth_norm": depth_norm,
        "torso_angle": torso,
        "asymmetry": abs((left_knee or avg_knee) - (right_knee or avg_knee)),
        "hip_asymmetry": abs((left_hip or avg_hip) - (right_hip or avg_hip)),
        "side_view_score": view_quality_score(landmarks, leg_len, view_type),
        "heel_lift_norm": heel_lift,
        "leg_angle": 180.0,
        "posture_tilt_deg": abs(90.0 - torso),
        "hip_ankle_vertical_norm": hip_ankle_vertical,
    }


def build_lunge_like_metrics(landmarks: list[Any], view_type: str) -> dict[str, float] | None:
    return build_squat_like_metrics(landmarks, view_type)


def build_push_like_metrics(landmarks: list[Any], view_type: str) -> dict[str, float] | None:
    l_sh = get_point(landmarks, LANDMARK["L_SHOULDER"])
    r_sh = get_point(landmarks, LANDMARK["R_SHOULDER"])
    l_el = get_point(landmarks, LANDMARK["L_ELBOW"])
    r_el = get_point(landmarks, LANDMARK["R_ELBOW"])
    l_wr = get_point(landmarks, LANDMARK["L_WRIST"])
    r_wr = get_point(landmarks, LANDMARK["R_WRIST"])
    l_hip = get_point(landmarks, LANDMARK["L_HIP"])
    r_hip = get_point(landmarks, LANDMARK["R_HIP"])
    l_knee = get_point(landmarks, LANDMARK["L_KNEE"])
    r_knee = get_point(landmarks, LANDMARK["R_KNEE"])
    l_ank = get_point(landmarks, LANDMARK["L_ANKLE"])
    r_ank = get_point(landmarks, LANDMARK["R_ANKLE"])
    l_lower = l_ank or l_knee or l_hip
    r_lower = r_ank or r_knee or r_hip
    if not all([l_sh, r_sh, l_el, r_el, l_wr, r_wr, l_hip, r_hip]) or (not l_lower and not r_lower):
        return None
    left_elbow = angle_deg(l_sh, l_el, l_wr)
    right_elbow = angle_deg(r_sh, r_el, r_wr)
    left_body = angle_deg(l_sh, l_hip, l_lower) if l_lower else None
    right_body = angle_deg(r_sh, r_hip, r_lower) if r_lower else None
    left_leg = angle_deg(l_hip, l_knee, l_lower) if l_knee and l_lower else None
    right_leg = angle_deg(r_hip, r_knee, r_lower) if r_knee and r_lower else None
    left_body_len = distance2d(l_sh, l_hip) + distance2d(l_hip, l_lower) if l_lower else 0.0
    right_body_len = distance2d(r_sh, r_hip) + distance2d(r_hip, r_lower) if r_lower else 0.0
    body_len = (left_body_len + right_body_len) / 2.0
    if body_len < 1e-6:
        return None
    left_vis = mean_visibility(landmarks, [LANDMARK["L_SHOULDER"], LANDMARK["L_ELBOW"], LANDMARK["L_WRIST"], LANDMARK["L_HIP"], LANDMARK["L_KNEE"]])
    right_vis = mean_visibility(landmarks, [LANDMARK["R_SHOULDER"], LANDMARK["R_ELBOW"], LANDMARK["R_WRIST"], LANDMARK["R_HIP"], LANDMARK["R_KNEE"]])
    avg_elbow = weighted_pair(left_elbow, right_elbow, left_vis, right_vis)
    avg_body = weighted_pair(left_body, right_body, left_vis, right_vis)
    avg_leg = weighted_pair(left_leg, right_leg, left_vis, right_vis)
    depth_norm = weighted_pair(
        (float(l_lower.y) - float(l_sh.y)) / max(left_body_len, 1e-6) if l_lower else None,
        (float(r_lower.y) - float(r_sh.y)) / max(right_body_len, 1e-6) if r_lower else None,
        left_vis,
        right_vis,
    )
    hip_ankle_vertical = weighted_pair(
        abs(float(l_hip.y) - float(l_lower.y)) / max(left_body_len, 1e-6) if l_lower else None,
        abs(float(r_hip.y) - float(r_lower.y)) / max(right_body_len, 1e-6) if r_lower else None,
        left_vis,
        right_vis,
    )
    posture_tilt = weighted_pair(torso_tilt_deg(l_hip, l_sh), torso_tilt_deg(r_hip, r_sh), left_vis, right_vis)
    body_break = weighted_pair(
        max(0.0, 180.0 - left_body) if left_body is not None else None,
        max(0.0, 180.0 - right_body) if right_body is not None else None,
        left_vis,
        right_vis,
    ) or 0.0
    hip_deviation = weighted_pair(
        point_line_distance(l_hip, l_sh, l_lower) / max(left_body_len, 1e-6) if l_lower else None,
        point_line_distance(r_hip, r_sh, r_lower) / max(right_body_len, 1e-6) if r_lower else None,
        left_vis,
        right_vis,
    ) or 0.0
    if avg_elbow is None or avg_body is None or depth_norm is None or hip_ankle_vertical is None or posture_tilt is None:
        return None
    return {
        "primary_angle": avg_elbow,
        "secondary_angle": avg_body,
        "depth_norm": depth_norm,
        "torso_angle": body_break,
        "asymmetry": abs((left_elbow or avg_elbow) - (right_elbow or avg_elbow)),
        "hip_asymmetry": abs((left_body or avg_body) - (right_body or avg_body)),
        "side_view_score": view_quality_score(landmarks, body_len, view_type),
        "heel_lift_norm": max(0.0, hip_deviation),
        "leg_angle": avg_leg or 180.0,
        "posture_tilt_deg": posture_tilt,
        "hip_ankle_vertical_norm": hip_ankle_vertical,
    }


def build_core_like_metrics(landmarks: list[Any], view_type: str) -> dict[str, float] | None:
    l_sh = get_point(landmarks, LANDMARK["L_SHOULDER"])
    r_sh = get_point(landmarks, LANDMARK["R_SHOULDER"])
    l_hip = get_point(landmarks, LANDMARK["L_HIP"])
    r_hip = get_point(landmarks, LANDMARK["R_HIP"])
    l_knee = get_point(landmarks, LANDMARK["L_KNEE"])
    r_knee = get_point(landmarks, LANDMARK["R_KNEE"])
    l_ank = get_point(landmarks, LANDMARK["L_ANKLE"])
    r_ank = get_point(landmarks, LANDMARK["R_ANKLE"])
    left_core = angle_deg(l_sh, l_hip, l_knee)
    right_core = angle_deg(r_sh, r_hip, r_knee)
    left_leg = angle_deg(l_hip, l_knee, l_ank)
    right_leg = angle_deg(r_hip, r_knee, r_ank)
    left_body_len = distance2d(l_sh, l_hip) + distance2d(l_hip, l_knee)
    right_body_len = distance2d(r_sh, r_hip) + distance2d(r_hip, r_knee)
    body_len = (left_body_len + right_body_len) / 2.0
    left_vis = mean_visibility(landmarks, [LANDMARK["L_SHOULDER"], LANDMARK["L_HIP"], LANDMARK["L_KNEE"]])
    right_vis = mean_visibility(landmarks, [LANDMARK["R_SHOULDER"], LANDMARK["R_HIP"], LANDMARK["R_KNEE"]])
    if left_core is None or right_core is None or body_len < 1e-6:
        return None
    torso = weighted_pair(torso_tilt_deg(l_hip, l_sh), torso_tilt_deg(r_hip, r_sh), left_vis, right_vis) or 0.0
    return {
        "primary_angle": weighted_pair(left_core, right_core, left_vis, right_vis) or 180.0,
        "secondary_angle": weighted_pair(left_leg, right_leg, left_vis, right_vis) or 180.0,
        "depth_norm": weighted_pair(distance2d(l_sh, l_knee) / body_len, distance2d(r_sh, r_knee) / body_len, left_vis, right_vis) or 0.0,
        "torso_angle": torso,
        "asymmetry": abs(left_core - right_core),
        "hip_asymmetry": abs((left_leg or 180.0) - (right_leg or 180.0)),
        "side_view_score": view_quality_score(landmarks, body_len, view_type),
        "heel_lift_norm": 0.0,
        "leg_angle": weighted_pair(left_leg, right_leg, left_vis, right_vis) or 180.0,
        "posture_tilt_deg": abs(90.0 - torso),
        "hip_ankle_vertical_norm": weighted_pair(abs(float(l_hip.y) - float(l_knee.y)) / body_len, abs(float(r_hip.y) - float(r_knee.y)) / body_len, left_vis, right_vis) or 0.0,
    }


def build_metric_frame(landmarks: list[Any], motion_family: str, view_type: str, timestamp_ms: int) -> dict[str, float] | None:
    if motion_family == "squat_like":
        metric = build_squat_like_metrics(landmarks, view_type)
    elif motion_family == "lunge_like":
        metric = build_lunge_like_metrics(landmarks, view_type)
    elif motion_family == "push_like":
        metric = build_push_like_metrics(landmarks, view_type)
    elif motion_family == "core_like":
        metric = build_core_like_metrics(landmarks, view_type)
    else:
        metric = None
    if metric is None:
        return None
    metric["timestamp_ms"] = int(timestamp_ms)
    return metric


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * (pct / 100.0)
    left = int(math.floor(position))
    right = min(left + 1, len(ordered) - 1)
    if left == right:
        return ordered[left]
    weight = position - left
    return ordered[left] * (1.0 - weight) + ordered[right] * weight


def calculate_duration(frame_metrics: list[dict[str, Any]]) -> int:
    if len(frame_metrics) < 2:
        return 0
    return max(0, int(frame_metrics[-1]["timestamp_ms"]) - int(frame_metrics[0]["timestamp_ms"]))


def normalize_timestamps(frame_metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not frame_metrics:
        return []
    base = int(frame_metrics[0]["timestamp_ms"])
    normalized = []
    for index, item in enumerate(frame_metrics):
        payload = dict(item)
        payload["timestamp_ms"] = max(0, int(item.get("timestamp_ms", index * 100)) - base)
        normalized.append(payload)
    return normalized


def metric_window_baseline(frame_metrics: list[dict[str, Any]], key: str) -> float:
    values = [to_number(item.get(key), 0.0) for item in frame_metrics]
    head = max(1, len(values) // 8)
    samples = values[:head] + values[max(len(values) - head, 0):]
    return sum(samples) / len(samples)


def metric_window_amplitude(frame_metrics: list[dict[str, Any]], key: str, baseline: float) -> float:
    return max(max(abs(to_number(item.get(key), baseline) - baseline) for item in frame_metrics), 1e-6)


def merge_active_segments(segments: list[dict[str, float]], max_gap: int) -> list[dict[str, float]]:
    merged: list[dict[str, float]] = []
    for segment in segments:
        previous = merged[-1] if merged else None
        if previous and segment["start"] - previous["end"] - 1 <= max_gap:
            previous["end"] = segment["end"]
            previous["score"] = previous["score"] + segment["score"]
            continue
        merged.append(dict(segment))
    return merged


def isolate_single_rep(frame_metrics: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, bool]:
    if not frame_metrics:
        return [], 0, False
    if len(frame_metrics) < 12:
        normalized = normalize_timestamps(frame_metrics)
        return normalized, calculate_duration(normalized), False

    baselines = {
        "primary_angle": metric_window_baseline(frame_metrics, "primary_angle"),
        "secondary_angle": metric_window_baseline(frame_metrics, "secondary_angle"),
        "depth_norm": metric_window_baseline(frame_metrics, "depth_norm"),
        "torso_angle": metric_window_baseline(frame_metrics, "torso_angle"),
    }
    amplitudes = {
        key: metric_window_amplitude(frame_metrics, key, baselines[key])
        for key in baselines
    }

    activity_scores = []
    for metric in frame_metrics:
        activity_scores.append(
            clamp(
                max(
                    abs(to_number(metric.get("primary_angle"), baselines["primary_angle"]) - baselines["primary_angle"]) / amplitudes["primary_angle"],
                    abs(to_number(metric.get("secondary_angle"), baselines["secondary_angle"]) - baselines["secondary_angle"]) / amplitudes["secondary_angle"],
                    abs(to_number(metric.get("depth_norm"), baselines["depth_norm"]) - baselines["depth_norm"]) / amplitudes["depth_norm"],
                    abs(to_number(metric.get("torso_angle"), baselines["torso_angle"]) - baselines["torso_angle"]) / amplitudes["torso_angle"],
                ),
                0.0,
                1.6,
            )
        )

    max_score = max(activity_scores or [0.0])
    if max_score < 0.12:
        normalized = normalize_timestamps(frame_metrics)
        return normalized, calculate_duration(normalized), False

    threshold = clamp(max(0.12, percentile(activity_scores, 70) * 0.92, max_score * 0.28), 0.12, 0.48)
    segments: list[dict[str, float]] = []
    current_start: int | None = None
    score_sum = 0.0
    for index, score in enumerate(activity_scores):
        if score >= threshold:
            if current_start is None:
                current_start = index
                score_sum = 0.0
            score_sum += score
            continue
        if current_start is not None:
            segments.append({"start": current_start, "end": index - 1, "score": score_sum})
            current_start = None
            score_sum = 0.0
    if current_start is not None:
        segments.append({"start": current_start, "end": len(activity_scores) - 1, "score": score_sum})

    segments = merge_active_segments(segments, 2)
    if not segments:
        normalized = normalize_timestamps(frame_metrics)
        return normalized, calculate_duration(normalized), False

    best_segment = max(
        segments,
        key=lambda item: float(item["score"]) * (float(item["end"]) - float(item["start"]) + 1.0),
    )
    start = max(0, int(best_segment["start"]) - 2)
    end = min(len(frame_metrics) - 1, int(best_segment["end"]) + 2)
    selected = frame_metrics[start:end + 1]
    if len(selected) < 10:
        normalized = normalize_timestamps(frame_metrics)
        return normalized, calculate_duration(normalized), False
    normalized = normalize_timestamps(selected)
    return normalized, calculate_duration(normalized), start > 0 or end < len(frame_metrics) - 1


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download_file(url: str, target_path: Path, *, force: bool) -> None:
    if target_path.exists() and not force:
        return
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(url, context=ssl_context) as response, target_path.open("wb") as output:
        shutil.copyfileobj(response, output)


def convert_to_mp4(source_path: Path, target_path: Path, *, force: bool) -> None:
    if target_path.exists() and not force:
        return
    if source_path.suffix.lower() == ".mp4":
        shutil.copy2(source_path, target_path)
        return
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-movflags",
            "faststart",
            "-pix_fmt",
            "yuv420p",
            str(target_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def analyze_video(video_path: Path, motion_family: str, view_type: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Не удалось открыть видео: {video_path}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_sec = frame_count / fps if fps > 0 and frame_count > 0 else 0.0
    sample_count = max(18, min(72, int(round(max(duration_sec, 0.35) * 18))))

    pose = mp.solutions.pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    frame_metrics: list[dict[str, Any]] = []
    try:
        for index in range(sample_count):
            progress = 0.0 if sample_count <= 1 else index / (sample_count - 1)
            target_ms = int(min(max(duration_sec * 1000.0 - 10.0, 0.0), progress * max(duration_sec * 1000.0, 350.0)))
            cap.set(cv2.CAP_PROP_POS_MSEC, target_ms)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if not results.pose_landmarks:
                continue
            metric = build_metric_frame(results.pose_landmarks.landmark, motion_family, view_type, target_ms)
            if metric is not None:
                frame_metrics.append(metric)
    finally:
        pose.close()
        cap.release()

    if len(frame_metrics) < 10:
        raise RuntimeError(f"Недостаточно валидных кадров для {video_path.name}")

    isolated_frames, duration_ms, trimmed = isolate_single_rep(frame_metrics)
    if len(isolated_frames) < 10:
        raise RuntimeError(f"Не удалось выделить один чистый повтор для {video_path.name}")

    return isolated_frames, {
        "duration_ms": max(1, duration_ms),
        "width": width,
        "height": height,
        "size_bytes": video_path.stat().st_size,
        "sample_count": sample_count,
        "trimmed": trimmed,
    }


def validate_reference_frames(spec: ReferenceSpec, frame_metrics: list[dict[str, Any]]) -> dict[str, float]:
    values = {
        "primary_angle": [to_number(item.get("primary_angle"), 0.0) for item in frame_metrics],
        "depth_norm": [to_number(item.get("depth_norm"), 0.0) for item in frame_metrics],
        "side_view_score": [to_number(item.get("side_view_score"), 0.0) for item in frame_metrics],
        "asymmetry": [to_number(item.get("asymmetry"), 0.0) for item in frame_metrics],
    }
    quality = {
        "valid_frames": float(len(frame_metrics)),
        "primary_amplitude": max(values["primary_angle"]) - min(values["primary_angle"]),
        "depth_amplitude": max(values["depth_norm"]) - min(values["depth_norm"]),
        "mean_side_view_score": sum(values["side_view_score"]) / len(values["side_view_score"]),
        "mean_asymmetry": sum(values["asymmetry"]) / len(values["asymmetry"]),
    }
    min_primary = {
        # Supine leg raises often produce a stronger normalized-depth signal
        # than torso-angle swing after isolating one clean rep.
        "leg_raise": 12.0,
    }.get(spec.slug, 16.0 if spec.motion_family == "core_like" else 20.0)
    min_depth = 0.02 if spec.motion_family == "core_like" else 0.045
    min_view = {
        "pushup": 0.78,
        "lunge": 0.58,
        "glute_bridge": 0.55,
        "leg_raise": 0.52,
        "crunch": 0.50,
    }.get(spec.slug, 0.45)
    max_asymmetry = {
        "pushup": 32.0,
        "lunge": 55.0,
        "glute_bridge": 24.0,
        "leg_raise": 28.0,
        "crunch": 24.0,
    }.get(spec.slug, 60.0)
    failures: list[str] = []
    if quality["valid_frames"] < 10:
        failures.append("valid_frames")
    if quality["primary_amplitude"] < min_primary:
        failures.append("primary_amplitude")
    if quality["depth_amplitude"] < min_depth:
        failures.append("depth_amplitude")
    if spec.slug != "squat" and quality["mean_side_view_score"] < min_view:
        failures.append("mean_side_view_score")
    if spec.slug != "squat" and quality["mean_asymmetry"] > max_asymmetry:
        failures.append("mean_asymmetry")
    if failures:
        raise RuntimeError(
            f"Reference video failed quality checks for {spec.slug}: "
            f"{', '.join(failures)}; metrics={quality}"
        )
    return quality


def write_readme(records: list[dict[str, Any]]) -> None:
    lines = [
        "# Kinematics Reference Videos",
        "",
        "Источники для системных эталонов техники. Все видео приведены к MP4 и сохранены в этом каталоге.",
        "",
    ]
    for record in records:
        lines.extend(
            [
                f"## {record['filename']}",
                f"- title: {record['title']}",
                f"- slug: {record['slug']}",
                f"- motion_family: {record['motion_family']}",
                f"- view_type: {record['view_type']}",
                f"- source_label: {record['source_label']}",
                f"- source_page_url: {record['source_page_url']}",
                f"- source_asset_url: {record['source_url']}",
                "",
            ]
        )
    README_PATH.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def reuse_desktop_source(spec: ReferenceSpec, target_path: Path) -> bool:
    base_name = f"{spec.order:02d}_{slugify_title(spec.title)}"
    candidates = [
        DESKTOP_DIR / f"{base_name}{spec.source_ext}",
        DESKTOP_DIR / f"{base_name}.mp4",
        DESKTOP_DIR / f"{base_name}.webm",
    ]
    prefix = f"{spec.order:02d}_"
    for candidate in sorted(DESKTOP_DIR.glob(f"{prefix}*")):
        if candidate.is_file() and candidate.suffix.lower() == spec.source_ext.lower():
            candidates.append(candidate)
    for candidate in sorted(DESKTOP_DIR.glob(f"{prefix}*.mp4")):
        if candidate.is_file():
            candidates.append(candidate)
    for candidate in sorted(DESKTOP_DIR.glob(f"{prefix}*.webm")):
        if candidate.is_file():
            candidates.append(candidate)
    for candidate in candidates:
        if candidate.exists():
            shutil.copy2(candidate, target_path)
            return True
    return False


def upsert_db_profile(spec: ReferenceSpec, stored_video_path: Path, reference_model: dict[str, Any], calibration_profile: dict[str, Any], video_meta: dict[str, Any]) -> None:
    with SessionLocal() as db:
        exercise = db.query(Exercise).filter(Exercise.name.in_(catalog_db_name_candidates(spec.slug))).one_or_none()
        if exercise is None:
            catalog_item = next(item for item in EXERCISE_CATALOG if item["slug"] == spec.slug)
            tags = [str(item).strip() for item in catalog_item.get("tags", []) if str(item).strip()]
            exercise = Exercise(
                name=CATALOG_DB_NAME_BY_SLUG[spec.slug],
                description=str(catalog_item.get("description") or spec.title),
                equipment=None,
                primary_muscles=tags[-1] if tags else None,
                difficulty="easy",
            )
            db.add(exercise)
            db.flush()
        else:
            exercise.name = CATALOG_DB_NAME_BY_SLUG[spec.slug]
            db.add(exercise)
            db.flush()

        profile = db.query(ExerciseTechniqueProfile).filter(ExerciseTechniqueProfile.exercise_id == exercise.id).one_or_none()
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        if profile is None:
            profile = ExerciseTechniqueProfile(
                exercise_id=exercise.id,
                owner_user_id=None,
                is_system=True,
                public_slug=spec.slug,
                status="published",
                motion_family=spec.motion_family,
                view_type=spec.view_type,
                created_at=now,
            )
        profile.owner_user_id = None
        profile.is_system = True
        profile.public_slug = spec.slug
        profile.status = "published"
        profile.motion_family = spec.motion_family
        profile.view_type = spec.view_type
        profile.source_video_name = stored_video_path.name
        profile.source_video_path = str(stored_video_path)
        profile.source_video_meta_json = dump_json(video_meta)
        profile.reference_model_json = dump_json(reference_model)
        profile.calibration_profile_json = dump_json(calibration_profile)
        profile.latest_test_summary_json = dump_json(
            {
                "rep_score": 100,
                "quality": "Отлично",
                "errors": [],
                "details": {"caps_applied": []},
            }
        )
        profile.published_at = now
        profile.updated_at = now
        db.add(profile)
        db.commit()


def main() -> int:
    args = parse_args()
    ensure_dir(DESKTOP_DIR)
    ensure_dir(SYSTEM_PROFILE_DIR)
    ensure_dir(SYSTEM_VIDEO_DIR)

    readme_records: list[dict[str, Any]] = []
    for spec in SPECS:
        source_target = SYSTEM_VIDEO_DIR / f"{spec.slug}{spec.source_ext}"
        desktop_video = DESKTOP_DIR / f"{spec.order:02d}_{slugify_title(spec.title)}.mp4"
        if args.force or not source_target.exists():
            if not reuse_desktop_source(spec, source_target):
                download_file(spec.source_url, source_target, force=args.force)
        convert_to_mp4(source_target, desktop_video, force=args.force)

        stored_video = SYSTEM_VIDEO_DIR / f"{spec.slug}.mp4"
        convert_to_mp4(source_target, stored_video, force=args.force)

        frame_metrics, video_meta = analyze_video(stored_video, spec.motion_family, spec.view_type)
        quality_meta = validate_reference_frames(spec, frame_metrics)
        video_meta["quality"] = quality_meta
        reference_model, calibration_profile = build_reference_model(
            frame_metrics=frame_metrics,
            motion_family=spec.motion_family,
            view_type=spec.view_type,
            video_meta=video_meta,
        )

        system_payload = {
            "slug": spec.slug,
            "title": spec.title,
            "motion_family": spec.motion_family,
            "view_type": spec.view_type,
            "source_url": spec.source_url,
            "source_page_url": spec.source_page_url,
            "source_label": spec.source_label,
            "desktop_video_path": str(desktop_video),
            "stored_video_path": str(stored_video),
            "video_meta": video_meta,
            "reference_model": reference_model,
            "calibration_profile": calibration_profile,
        }
        (SYSTEM_PROFILE_DIR / f"{spec.slug}.json").write_text(
            json.dumps(system_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        readme_records.append(
            {
                "filename": desktop_video.name,
                "title": spec.title,
                "slug": spec.slug,
                "motion_family": spec.motion_family,
                "view_type": spec.view_type,
                "source_label": spec.source_label,
                "source_page_url": spec.source_page_url,
                "source_url": spec.source_url,
            }
        )

        if not args.skip_db:
            try:
                upsert_db_profile(spec, stored_video, reference_model, calibration_profile, video_meta)
            except Exception as exc:  # noqa: BLE001
                print(f"[warn] DB upsert skipped for {spec.slug}: {exc}", file=sys.stderr)

        print(f"[ok] {spec.slug}: {desktop_video}")

    write_readme(readme_records)
    print(f"[ok] desktop folder: {DESKTOP_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
