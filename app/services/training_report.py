from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.exercise_catalog import CATALOG_TITLE_BY_SLUG

try:
    from huggingface_hub import hf_hub_download, list_repo_files
except ImportError:  # pragma: no cover
    hf_hub_download = None
    list_repo_files = None

try:
    from llama_cpp import Llama
except ImportError:  # pragma: no cover
    Llama = None

HF_REPO_ID = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
LLM_MODELS_DIR = Path("data/llm_models")
REPORTS_DIR = Path("data/session_reports")
REPORTS_DIR_RESOLVED = REPORTS_DIR.resolve()
LOGS_DIR = Path("data/session_logs").resolve()

SYSTEM_PROMPT = (
    "Ты — ассистент-тренер по технике упражнений. Используй ТОЛЬКО данные из JSON пользователя. "
    "Ничего не додумывай. Если данных не хватает — пиши 'нет данных'. Сформируй краткий и понятный отчёт "
    "о тренировке: 1) итог (score/качество), 2) топ-3 ошибки техники, 3) конкретные рекомендации как исправить, "
    "4) флаги риска/безопасности. Каждая рекомендация должна иметь 'Основание' — ссылку на конкретное поле/метрику/ошибку "
    "из JSON. Пиши на русском. Не упоминай, что ты ИИ."
)

FIRST_USER_PROMPT = (
    "Верни ответ обычным текстом без Markdown и без JSON-дампа. "
    "Сделай блоки в таком порядке: Итог, Топ-3 ошибки техники, Что делать в следующем подходе, "
    "Риски/безопасность, Фокус на следующий подход. "
    "Каждая рекомендация обязана содержать строку 'Основание: ...'. "
    "Если данных не хватает — пиши 'нет данных'."
)

RETRY_REMINDER = (
    "КРИТИЧНО: не добавляй ничего вне JSON. Никаких предположений. "
    "Не используй формулировки в стиле ИИ-ассистента. "
    "Пиши короткими бытовыми фразами. "
    "Если данных нет — пиши 'нет данных'. "
    "Каждая рекомендация обязана содержать строку 'Основание: ...'."
)

MAX_JSON_PROMPT_CHARS = 2200

SEVERITY_LABELS = {
    "high": "высокий приоритет",
    "med": "средний приоритет",
    "low": "низкий приоритет",
}

METRIC_LABELS = {
    "min_knee_angle": "глубина приседа в колене",
    "min_hip_angle": "глубина приседа в тазобедренном суставе",
    "max_depth_delta": "стабильность амплитуды",
    "depth_ratio": "рабочая глубина",
    "knee_ratio": "контроль траектории колена",
    "hip_ratio": "контроль таза",
    "max_torso_forward": "наклон корпуса",
    "p90_heel_lift": "отрыв пяток",
    "mean_side_view_score": "боковой ракурс",
    "min_elbow_angle": "глубина сгибания локтя",
    "min_leg_knee_angle": "линия ног",
    "p90_depth_delta": "стабильность глубины отжиманий",
    "depth_ratio_raw": "провал в нижней точке",
    "elbow_ratio": "угол локтя",
    "p90_body_bend": "линия корпуса",
}

ISSUE_TITLE_BY_CODE = {
    "knee_depth_control": "Контроль глубины в колене",
    "hip_depth_control": "Контроль глубины в тазу",
    "depth_stability": "Нестабильная амплитуда",
    "depth_ratio_mismatch": "Отклонение рабочей глубины",
    "knee_ratio_mismatch": "Отклонение по траектории колена",
    "hip_ratio_mismatch": "Отклонение по работе таза",
    "torso_forward": "Избыточный наклон корпуса",
    "heel_lift": "Отрыв пяток",
    "undersquat": "Недостаточная глубина приседа",
    "asymmetry": "Асимметрия сторон",
    "camera_side_view": "Недостаточный боковой ракурс",
    "elbow_depth_control": "Нестабильная глубина локтя",
    "push_depth_stability": "Плавающая глубина отжиманий",
    "excessive_depth_drop": "Провал в нижней точке",
    "elbow_ratio_mismatch": "Отклонение по работе локтя",
    "body_line_break": "Потеря линии корпуса",
}

RECOMMENDATION_ACTIONS_BY_CODE: dict[str, dict[str, Any]] = {
    "knee_depth_control": {
        "advice": "Сделайте одинаковую глубину колена в каждом приседе.",
        "steps": [
            "Опускайтесь на счёт «раз-два» без ускорения вниз.",
            "Внизу задержитесь на полсекунды.",
            "Если глубина отличается, повтор не засчитывайте и сделайте заново.",
        ],
    },
    "hip_depth_control": {
        "advice": "Держите таз на одной глубине без провала.",
        "steps": [
            "Выберите рабочую нижнюю точку и держите её в каждом повторе.",
            "Если таз проваливается, уменьшите скорость опускания.",
            "Поднимайтесь только из стабильной позиции.",
        ],
    },
    "depth_stability": {
        "advice": "Уберите «плавающую» амплитуду между повторами.",
        "steps": [
            "Первый повтор используйте как эталон глубины.",
            "Повторяйте ту же амплитуду на каждом следующем повторе.",
            "При потере амплитуды сделайте 10 секунд паузы и продолжите.",
        ],
    },
    "torso_forward": {
        "advice": "Снизьте лишний наклон корпуса вперёд.",
        "steps": [
            "Перед началом повтора поднимите грудь и зафиксируйте спину.",
            "Держите вес в середине стопы.",
            "Если корпус заваливается, уменьшите глубину на 1-2 повтора.",
        ],
    },
    "heel_lift": {
        "advice": "Держите пятки на полу в каждом повторе.",
        "steps": [
            "Перенесите давление на середину стопы и пятку.",
            "При отрыве пяток сразу уменьшите глубину.",
            "Возвращайте глубину постепенно, когда пятки остаются на полу.",
        ],
    },
    "elbow_depth_control": {
        "advice": "Сделайте одинаковую глубину сгибания локтей в отжиманиях.",
        "steps": [
            "Опускайтесь до одной и той же нижней точки.",
            "Не меняйте глубину от повтора к повтору.",
            "Если глубина падает, сделайте короткую паузу и продолжите.",
        ],
    },
    "push_depth_stability": {
        "advice": "Удерживайте одинаковую глубину на всех отжиманиях.",
        "steps": [
            "Работайте в одном темпе вниз и вверх.",
            "Коротко фиксируйте нижнюю фазу без провала.",
            "Засчитывайте только повторы с одинаковой амплитудой.",
        ],
    },
    "body_line_break": {
        "advice": "Держите корпус прямой линией во всём повторе.",
        "steps": [
            "Перед повтором включите пресс и ягодицы.",
            "Не допускайте провала в пояснице.",
            "Остановите повтор, если линия корпуса сломалась.",
        ],
    },
}


class ReportGenerationError(RuntimeError):
    pass


class ReportDependencyError(RuntimeError):
    pass


@dataclass(slots=True)
class TrainingReportResult:
    report_markdown: str
    report_path: Path
    avg_score: float | None


_llm_instance: Any = None
_model_path: Path | None = None
_llm_lock = Lock()


def _ensure_dependencies() -> None:
    if hf_hub_download is None or list_repo_files is None:
        raise ReportDependencyError(
            "Не установлена зависимость huggingface_hub. Установите её в окружение backend."
        )
    if Llama is None:
        raise ReportDependencyError(
            "Не установлена зависимость llama-cpp-python. Установите её в окружение backend."
        )


def _select_gguf_filename(repo_files: list[str]) -> str:
    gguf_files = sorted([name for name in repo_files if name.lower().endswith(".gguf")], key=str.lower)
    if not gguf_files:
        raise ReportGenerationError(f"В репозитории {HF_REPO_ID} не найдено GGUF-файлов.")

    for name in gguf_files:
        if "q4_k_m" in name.lower():
            return name

    for name in gguf_files:
        lowered = name.lower()
        if "q4" in lowered and "instruct" in lowered:
            return name

    return gguf_files[0]


def _resolve_model_path() -> Path:
    global _model_path

    if _model_path is not None and _model_path.exists():
        return _model_path

    _ensure_dependencies()
    LLM_MODELS_DIR.mkdir(parents=True, exist_ok=True)

    repo_files = list_repo_files(repo_id=HF_REPO_ID)
    selected_name = _select_gguf_filename(repo_files)
    logging.info("Для генерации отчёта выбран GGUF: %s", selected_name)

    model_path = hf_hub_download(
        repo_id=HF_REPO_ID,
        filename=selected_name,
        local_dir=str(LLM_MODELS_DIR),
    )
    _model_path = Path(model_path).resolve()
    return _model_path


def _compute_threads() -> int:
    cpus = os.cpu_count() or 4
    return max(4, cpus // 2)


def _extract_content(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message")

    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()

    text = first.get("text")
    if isinstance(text, str):
        return text.strip()

    return ""


def _get_llm() -> Any:
    global _llm_instance

    if _llm_instance is not None:
        return _llm_instance

    with _llm_lock:
        if _llm_instance is not None:
            return _llm_instance

        model_path = _resolve_model_path()
        _llm_instance = Llama(
            model_path=str(model_path),
            n_ctx=8192,
            n_threads=_compute_threads(),
            verbose=False,
        )

    return _llm_instance


def _build_user_prompt(json_text: str, strict: bool = False) -> str:
    instructions = FIRST_USER_PROMPT
    if strict:
        instructions = f"{FIRST_USER_PROMPT}\n\n{RETRY_REMINDER}"

    return (
        f"{instructions}\n\n"
        "Данные тренировки в JSON:\n"
        "```json\n"
        f"{json_text}\n"
        "```"
    )


def _section_block(text: str, start_keywords: tuple[str, ...], stop_keywords: tuple[str, ...]) -> str:
    lines = text.splitlines()
    start_index: int | None = None

    for idx, line in enumerate(lines):
        lowered = line.strip().lower()
        if any(keyword in lowered for keyword in start_keywords):
            start_index = idx + 1
            break

    if start_index is None:
        return ""

    end_index = len(lines)
    for idx in range(start_index, len(lines)):
        lowered = lines[idx].strip().lower()
        if any(keyword in lowered for keyword in stop_keywords):
            end_index = idx
            break

    return "\n".join(lines[start_index:end_index]).strip()


SUMMARY_SECTION_HINTS = ("итог", "результат", "общая оценка")
ISSUES_SECTION_HINTS = ("топ-3", "топ 3", "ошибки техники", "ключевые ошибки", "главные ошибки")
RECOMMENDATIONS_SECTION_HINTS = ("что делать", "рекоменда", "советы", "дальше по технике", "как исправить")
RISKS_SECTION_HINTS = ("риски", "безопас")
FOCUS_SECTION_HINTS = ("фокус на следующий подход", "следующий подход", "мотивац")


def _normalize_report_text(text: str) -> str:
    raw = text.strip()
    if not raw:
        return ""

    summary = _section_block(
        raw,
        SUMMARY_SECTION_HINTS,
        ISSUES_SECTION_HINTS + RECOMMENDATIONS_SECTION_HINTS + RISKS_SECTION_HINTS + FOCUS_SECTION_HINTS,
    )
    issues = _section_block(
        raw,
        ISSUES_SECTION_HINTS,
        RECOMMENDATIONS_SECTION_HINTS + RISKS_SECTION_HINTS + FOCUS_SECTION_HINTS,
    )
    recommendations = _section_block(
        raw,
        RECOMMENDATIONS_SECTION_HINTS,
        RISKS_SECTION_HINTS + FOCUS_SECTION_HINTS,
    )
    risks = _section_block(raw, RISKS_SECTION_HINTS, FOCUS_SECTION_HINTS)
    focus = _section_block(raw, FOCUS_SECTION_HINTS, ())

    # Semantic fallback for recommendations if heading differs but evidence lines are present.
    if not recommendations:
        lower = raw.lower()
        if "основание:" in lower and ("совет" in lower or "рекоменд" in lower or "что делать" in lower):
            recommendations = raw

    blocks: list[str] = []
    blocks.append("Итог")
    blocks.append(summary or "нет данных")
    blocks.append("")
    blocks.append("Топ-3 ошибки техники")
    blocks.append(issues or "нет данных")
    blocks.append("")
    blocks.append("Что делать в следующем подходе")
    blocks.append(recommendations or "1. нет данных\n   Основание: нет данных")
    blocks.append("")
    blocks.append("Риски/безопасность")
    blocks.append(risks or "Критичных рисков по текущему логу не выявлено.")
    blocks.append("")
    blocks.append("Фокус на следующий подход")
    blocks.append(focus or "нет данных")
    return "\n".join(blocks).strip()


def _validate_report(text: str) -> tuple[bool, list[str]]:
    issues: list[str] = []
    normalized = text.strip()

    if not normalized:
        return False, ["пустой ответ"]

    lowered = normalized.lower()
    if not any(keyword in lowered for keyword in SUMMARY_SECTION_HINTS):
        issues.append("нет секции 'Итог'")
    if not any(keyword in lowered for keyword in ISSUES_SECTION_HINTS):
        issues.append("нет секции 'Топ-3 ошибки техники'")
    if not any(keyword in lowered for keyword in RECOMMENDATIONS_SECTION_HINTS):
        issues.append("нет секции рекомендаций")
    if not any(keyword in lowered for keyword in RISKS_SECTION_HINTS):
        issues.append("нет секции 'Риски/безопасность'")

    recommendation_text = _section_block(
        normalized,
        RECOMMENDATIONS_SECTION_HINTS,
        RISKS_SECTION_HINTS + FOCUS_SECTION_HINTS,
    )
    recommendations_count = len(
        re.findall(r"^\s*(?:[-*]|\d+[.)])\s+", recommendation_text, flags=re.MULTILINE)
    )
    evidence_count = len(re.findall(r"основание\s*:", recommendation_text, flags=re.IGNORECASE))

    if recommendation_text and evidence_count == 0:
        issues.append("в рекомендациях нет строк 'Основание:'")
    elif recommendations_count > 0 and evidence_count < recommendations_count:
        issues.append("не у каждой рекомендации есть строка 'Основание:'")

    return len(issues) == 0, issues


def _ensure_required_sections(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        normalized = "Итог\nнет данных"

    sections = [
        ("Итог", "нет данных"),
        ("Топ-3 ошибки техники", "нет данных"),
        (
            "Что делать в следующем подходе",
            "1. нет данных\n   Основание: нет данных",
        ),
        ("Риски/безопасность", "Критичных рисков по текущему логу не выявлено."),
        ("Фокус на следующий подход", "нет данных"),
    ]

    result = normalized
    lowered = result.lower()
    for heading, fallback in sections:
        if heading.lower() not in lowered:
            result = f"{result}\n\n{heading}\n{fallback}"
            lowered = result.lower()

    return result.strip()


def _generate_with_llm(json_text: str, strict_retry: bool = False) -> str:
    llm = _get_llm()
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(json_text, strict=strict_retry)},
        ],
        temperature=0.15,
        max_tokens=700,
    )
    return _extract_content(response)


def _safe_avg_score(payload: dict[str, Any]) -> float | None:
    aggregates = payload.get("aggregates")
    if not isinstance(aggregates, dict):
        return None

    raw_avg = aggregates.get("avgScore")
    if isinstance(raw_avg, (int, float)):
        return float(raw_avg)

    return None


def _legacy_quality_label(score: float | None) -> str:
    if score is None:
        return "нужно улучшить"
    if score >= 90:
        return "отлично"
    if score >= 75:
        return "хорошо"
    if score >= 60:
        return "норм"
    return "нужно улучшить"


def _legacy_motivation(quality_label: str) -> str:
    mapping = {
        "отлично": "Сильный подход, закрепляйте текущую технику.",
        "хорошо": "Хороший результат, доведите стабильность до уровня «отлично».",
        "норм": "Нормальный уровень, сфокусируйтесь на ключевых корректировках.",
        "нужно улучшить": "Есть зона роста, снизьте темп и отработайте технику по шагам.",
    }
    return mapping.get(quality_label, mapping["нужно улучшить"])


def _build_legacy_ui_fallback(payload: dict[str, Any]) -> dict[str, Any]:
    score = _safe_avg_score(payload)
    reps = payload.get("reps")
    reps_count = len(reps) if isinstance(reps, list) else 0
    quality_label = _legacy_quality_label(score)

    aggregates = payload.get("aggregates")
    summary_tips: list[str] = []
    if isinstance(aggregates, dict) and isinstance(aggregates.get("summaryTips"), list):
        summary_tips = [str(item).strip() for item in aggregates.get("summaryTips", []) if str(item).strip()]

    recommendations: list[dict[str, Any]] = []
    for idx, tip in enumerate(summary_tips[:5]):
        recommendations.append(
            {
                "advice": tip,
                "steps": [
                    "Сделайте 2 медленных разминочных повтора с контролем амплитуды.",
                    "Сохраните тот же темп в следующем рабочем повторе.",
                ],
                "evidenceRef": f"aggregates.summaryTips[{idx}]",
            }
        )

    return {
        "summary": {
            "score": score,
            "qualityLabel": quality_label,
            "repsCount": reps_count,
        },
        "topIssues": [],
        "recommendations": recommendations,
        "risks": [],
        "motivation": _legacy_motivation(quality_label),
    }


def _limit_text(value: Any, max_len: int = 180) -> str:
    text = str(value).strip() if value is not None else ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _compact_ui_for_prompt(ui_payload: dict[str, Any]) -> dict[str, Any]:
    summary = ui_payload.get("summary", {}) if isinstance(ui_payload.get("summary"), dict) else {}
    top_issues_raw = ui_payload.get("topIssues", [])
    top_issues: list[dict[str, Any]] = []
    if isinstance(top_issues_raw, list):
        for issue in top_issues_raw[:3]:
            if not isinstance(issue, dict):
                continue
            top_issues.append(
                {
                    "code": issue.get("code"),
                    "title": _limit_text(issue.get("title"), 120),
                    "explanation": _limit_text(issue.get("explanation"), 180),
                    "severity": issue.get("severity"),
                    "evidenceRef": issue.get("evidenceRef"),
                }
            )

    recommendations_raw = ui_payload.get("recommendations", [])
    recommendations: list[dict[str, Any]] = []
    if isinstance(recommendations_raw, list):
        for item in recommendations_raw[:4]:
            if not isinstance(item, dict):
                continue
            steps_raw = item.get("steps", [])
            steps: list[str] = []
            if isinstance(steps_raw, list):
                steps = [_limit_text(step, 120) for step in steps_raw[:2]]
            recommendations.append(
                {
                    "advice": _limit_text(item.get("advice"), 160),
                    "steps": steps,
                    "evidenceRef": item.get("evidenceRef"),
                }
            )

    risks_raw = ui_payload.get("risks", [])
    risks: list[dict[str, Any]] = []
    if isinstance(risks_raw, list):
        for item in risks_raw[:3]:
            if not isinstance(item, dict):
                continue
            risks.append(
                {
                    "title": _limit_text(item.get("title"), 120),
                    "description": _limit_text(item.get("description"), 160),
                    "evidenceRef": item.get("evidenceRef"),
                }
            )

    return {
        "summary": summary,
        "topIssues": top_issues,
        "recommendations": recommendations,
        "risks": risks,
        "motivation": _limit_text(ui_payload.get("motivation"), 140),
    }


def _compact_report_for_prompt(report_payload: dict[str, Any], rep_limit: int = 6) -> dict[str, Any]:
    summary = report_payload.get("summary", {}) if isinstance(report_payload.get("summary"), dict) else {}
    rule_flags = report_payload.get("ruleFlags", {}) if isinstance(report_payload.get("ruleFlags"), dict) else {}
    depth_stats = report_payload.get("depthStats", {}) if isinstance(report_payload.get("depthStats"), dict) else {}
    penalty_stats = report_payload.get("penaltyStats", {}) if isinstance(report_payload.get("penaltyStats"), dict) else {}
    issue_stats = report_payload.get("issueStats", {}) if isinstance(report_payload.get("issueStats"), dict) else {}

    rep_breakdown_raw = report_payload.get("repBreakdown", [])
    rep_breakdown: list[dict[str, Any]] = []
    if isinstance(rep_breakdown_raw, list):
        for rep in rep_breakdown_raw[:rep_limit]:
            if not isinstance(rep, dict):
                continue
            rep_breakdown.append(
                {
                    "repIndex": rep.get("repIndex"),
                    "repScore": rep.get("repScore"),
                    "quality": rep.get("quality"),
                    "topErrors": [_limit_text(item, 100) for item in rep.get("topErrors", [])[:2]]
                    if isinstance(rep.get("topErrors"), list)
                    else [],
                    "topTips": [_limit_text(item, 100) for item in rep.get("topTips", [])[:2]]
                    if isinstance(rep.get("topTips"), list)
                    else [],
                    "scoreBreakdown": rep.get("scoreBreakdown", {}),
                }
            )

    metric_stats_raw = report_payload.get("metricStats", {})
    metric_stats: dict[str, Any] = {}
    if isinstance(metric_stats_raw, dict):
        for key in list(metric_stats_raw.keys())[:8]:
            value = metric_stats_raw.get(key)
            if not isinstance(value, dict):
                continue
            metric_stats[key] = {
                "min": value.get("min"),
                "max": value.get("max"),
                "mean": value.get("mean"),
                "p90": value.get("p90"),
            }

    compact_penalty_stats: dict[str, Any] = {}
    for key in list(penalty_stats.keys())[:6]:
        value = penalty_stats.get(key)
        if not isinstance(value, dict):
            continue
        compact_penalty_stats[key] = {
            "mean": value.get("mean"),
            "p90": value.get("p90"),
            "max": value.get("max"),
        }

    return {
        "version": report_payload.get("version", "v2"),
        "summary": summary,
        "ruleFlags": rule_flags,
        "depthStats": depth_stats,
        "penaltyStats": compact_penalty_stats,
        "issueStats": issue_stats,
        "repBreakdown": rep_breakdown,
        "metricStats": metric_stats,
        "promptReady": bool(report_payload.get("promptReady", False)),
    }


def _build_compact_prompt_payload(payload: dict[str, Any], rep_limit: int = 6) -> dict[str, Any]:
    meta = payload.get("meta")
    ui = payload.get("ui")
    report = payload.get("report")

    ui_source: dict[str, Any]
    if _has_ui_data(ui):
        ui_source = ui
    else:
        ui_source = _build_legacy_ui_fallback(payload)

    report_source = report if isinstance(report, dict) else {}

    return {
        "meta": meta if isinstance(meta, dict) else {},
        "report": _compact_report_for_prompt(report_source, rep_limit=rep_limit),
        "ui": _compact_ui_for_prompt(ui_source),
    }


def _to_prompt_json_text(payload: dict[str, Any]) -> str:
    for rep_limit in (8, 6, 4, 3, 2, 1):
        compact_payload = _build_compact_prompt_payload(payload, rep_limit=rep_limit)
        text = json.dumps(compact_payload, ensure_ascii=False, indent=2)
        if len(text) <= MAX_JSON_PROMPT_CHARS:
            return text

    compact_payload = _build_compact_prompt_payload(payload, rep_limit=1)
    report = compact_payload.get("report", {})
    ui = compact_payload.get("ui", {})
    ultra_minimal = {
        "meta": compact_payload.get("meta", {}),
        "report": {
            "version": report.get("version", "v2") if isinstance(report, dict) else "v2",
            "summary": report.get("summary", {}) if isinstance(report, dict) else {},
            "ruleFlags": report.get("ruleFlags", {}) if isinstance(report, dict) else {},
        },
        "ui": {
            "summary": ui.get("summary", {}) if isinstance(ui, dict) else {},
            "topIssues": (ui.get("topIssues", [])[:2] if isinstance(ui, dict) else []),
            "recommendations": (ui.get("recommendations", [])[:2] if isinstance(ui, dict) else []),
            "risks": (ui.get("risks", [])[:2] if isinstance(ui, dict) else []),
        },
    }
    ultra_text = json.dumps(ultra_minimal, ensure_ascii=False, indent=2)
    return ultra_text[:MAX_JSON_PROMPT_CHARS]


def _to_ultra_prompt_json_text(payload: dict[str, Any]) -> str:
    meta = payload.get("meta")
    ui = payload.get("ui")
    report = payload.get("report")

    if _has_ui_data(ui):
        ui_source = _compact_ui_for_prompt(ui)
    else:
        ui_source = _compact_ui_for_prompt(_build_legacy_ui_fallback(payload))

    report_source = report if isinstance(report, dict) else {}
    compact_report = _compact_report_for_prompt(report_source, rep_limit=1)

    tiny_payload = {
        "meta": {
            "exercise": (meta or {}).get("exercise") if isinstance(meta, dict) else None,
            "timestamp": (meta or {}).get("timestamp") if isinstance(meta, dict) else None,
        },
        "report": {
            "summary": compact_report.get("summary", {}),
            "ruleFlags": compact_report.get("ruleFlags", {}),
        },
        "ui": {
            "summary": ui_source.get("summary", {}),
            "topIssues": (ui_source.get("topIssues", [])[:2]),
            "recommendations": (ui_source.get("recommendations", [])[:2]),
            "risks": (ui_source.get("risks", [])[:2]),
            "motivation": ui_source.get("motivation", "нет данных"),
        },
    }
    return json.dumps(tiny_payload, ensure_ascii=False, separators=(",", ":"))[:1200]


def _normalize_log_path(log_path: Path) -> Path:
    resolved = log_path.expanduser().resolve()
    try:
        resolved.relative_to(LOGS_DIR)
    except ValueError as exc:
        raise ReportGenerationError("Запрошенный лог находится вне директории data/session_logs.") from exc
    return resolved


def _load_log_payload(log_path: Path, user_id: int) -> dict[str, Any]:
    if not log_path.exists() or not log_path.is_file():
        raise FileNotFoundError(f"JSON-лог не найден: {log_path}")

    try:
        payload = json.loads(log_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReportGenerationError("Файл лога содержит невалидный JSON.") from exc
    except OSError as exc:
        raise ReportGenerationError("Не удалось прочитать файл JSON-лога.") from exc

    if not isinstance(payload, dict):
        raise ReportGenerationError("Некорректная структура JSON-лога.")

    meta = payload.get("meta")
    if not isinstance(meta, dict):
        raise ReportGenerationError("В JSON-логе отсутствует блок meta.")

    owner_id = meta.get("userId")
    if owner_id is None:
        raise ReportGenerationError("В JSON-логе отсутствует meta.userId.")

    try:
        owner_id_int = int(owner_id)
    except (TypeError, ValueError) as exc:
        raise ReportGenerationError("meta.userId имеет некорректный формат.") from exc

    if owner_id_int != user_id:
        raise PermissionError("Лог принадлежит другому пользователю.")

    return payload


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    return None


def _to_clean_text(value: Any, fallback: str = "нет данных") -> str:
    text = str(value).strip() if value is not None else ""
    return text if text else fallback


def _metric_label_from_ref(ref: str) -> str:
    metric_key = ref.rsplit(".", 1)[-1]
    return METRIC_LABELS.get(metric_key, metric_key)


def _humanize_evidence_ref(ref: Any) -> str:
    raw = _to_clean_text(ref)
    if raw == "нет данных":
        return raw

    reps_match = re.match(r"^reps\[(\d+)\](?:\.(.+))?$", raw)
    if reps_match:
        rep_index = int(reps_match.group(1)) + 1
        tail = reps_match.group(2) or ""
        if tail.startswith("details.hint_codes"):
            return f"ошибка, зафиксированная в повторе №{rep_index}"
        if tail.startswith("errors"):
            return f"ошибка в повторе №{rep_index}"
        if tail.startswith("metrics."):
            metric_key = tail.split(".", 1)[1]
            return f"{_metric_label_from_ref(metric_key)} в повторе №{rep_index}"
        if tail.startswith("details.score_breakdown"):
            return f"расчёт оценки повтора №{rep_index}"
        return f"данные повтора №{rep_index}"

    if raw.startswith("aggregates.worstMetrics."):
        return _metric_label_from_ref(raw)
    if raw.startswith("ui.topIssues["):
        return "ключевая ошибка из сводки подхода"
    if raw.startswith("aggregates.summaryTips["):
        return "итоговая подсказка по подходу"

    if re.match(r"^[A-Za-z_]+(?:\[[0-9]+\])?(?:\.[A-Za-z_]+(?:\[[0-9]+\])?)*$", raw):
        return "данные текущего подхода"

    return raw


def _sanitize_evidence_lines(report_text: str) -> str:
    lines = report_text.splitlines()
    sanitized: list[str] = []
    for line in lines:
        if re.search(r"основание\s*:", line, flags=re.IGNORECASE):
            prefix, _, value = line.partition(":")
            humanized = _humanize_evidence_ref(value.strip())
            indent = ""
            leading_ws = re.match(r"^\s*", line)
            if leading_ws:
                indent = leading_ws.group(0)
            sanitized.append(f"{indent}{prefix.strip()}: {humanized}")
            continue
        sanitized.append(line)
    return "\n".join(sanitized)


def _format_steps(steps: Any) -> list[str]:
    if not isinstance(steps, list):
        return []
    result: list[str] = []
    for item in steps:
        text = _to_clean_text(item, fallback="")
        if not text:
            continue
        result.append(text)
    return result


def _has_ui_data(ui_payload: Any) -> bool:
    if not isinstance(ui_payload, dict):
        return False
    for key in ("summary", "topIssues", "recommendations", "risks", "motivation"):
        if key in ui_payload:
            return True
    return False


def _normalize_issue_title(title: Any, code: Any) -> str:
    title_text = _to_clean_text(title)
    code_text = _to_clean_text(code, fallback="").strip().lower()
    if not code_text:
        return title_text

    if (
        title_text.lower().startswith("проблема:")
        or title_text.strip().lower() == code_text
        or re.search(r"[a-z_]{4,}", title_text) is not None
    ):
        return ISSUE_TITLE_BY_CODE.get(code_text, "Техническое отклонение")
    return title_text


def _exercise_title(exercise_slug: Any) -> str:
    slug = _to_clean_text(exercise_slug, fallback="").lower()
    return CATALOG_TITLE_BY_SLUG.get(
        slug,
        _to_clean_text(exercise_slug, fallback="Тренировка"),
    )


def _flag_reps(report_payload: dict[str, Any], key: str) -> set[int]:
    if not isinstance(report_payload, dict):
        return set()
    rule_flags = report_payload.get("ruleFlags")
    if not isinstance(rule_flags, dict):
        return set()
    raw_items = rule_flags.get(key)
    if not isinstance(raw_items, list):
        return set()
    result: set[int] = set()
    for item in raw_items:
        try:
            result.add(int(item))
        except (TypeError, ValueError):
            continue
    return result


def _is_low_quality_llm_report(report_text: str) -> bool:
    lowered = report_text.strip().lower()
    if not lowered:
        return True
    if "итог\nнет данных" in lowered:
        return True
    if "что делать в следующем подходе\n1. нет данных" in lowered:
        return True
    return lowered.count("нет данных") >= 3


def build_report_from_ui(
    ui_payload: dict[str, Any],
    meta_payload: dict[str, Any] | None = None,
    report_payload: dict[str, Any] | None = None,
) -> str:
    meta = meta_payload if isinstance(meta_payload, dict) else {}
    report = report_payload if isinstance(report_payload, dict) else {}
    summary = ui_payload.get("summary") if isinstance(ui_payload.get("summary"), dict) else {}

    score = _to_float(summary.get("score"))
    quality_label = _to_clean_text(summary.get("qualityLabel"), fallback="нет данных")
    reps_count = _to_int(summary.get("repsCount"))

    exercise = _exercise_title(meta.get("exercise"))
    heel_fail_reps = _flag_reps(report, "heelFailReps")
    undersquat_reps = _flag_reps(report, "undersquatReps")
    good_pose_reps = _flag_reps(report, "goodPoseReps")
    technique_problem_reps = heel_fail_reps | undersquat_reps

    lines: list[str] = []
    lines.append("Итог")
    lines.append(f"Упражнение: {exercise}.")
    if score is None:
        lines.append("Общая оценка: данных недостаточно.")
    else:
        lines.append(f"Общая оценка: {score:.1f}/100")
    lines.append(f"Качество подхода: {quality_label}.")
    if reps_count is None:
        lines.append("Количество повторов: данных недостаточно.")
    else:
        lines.append(f"Количество повторов: {reps_count}.")

    if reps_count is not None and reps_count < 6:
        lines.append(
            "Подход пока короткий: вы выполнили только часть запланированного объёма. "
            "Сделайте ещё 2-4 повторения в таком же контролируемом темпе."
        )

    if good_pose_reps and technique_problem_reps:
        lines.append(
            f"Есть качественные повторы ({len(good_pose_reps)}), но техника местами хромает "
            f"({len(technique_problem_reps)} повтора с ошибками)."
        )
    elif good_pose_reps and not technique_problem_reps:
        lines.append("Повторы в целом получаются чистыми, продолжайте в том же темпе.")
    elif technique_problem_reps:
        lines.append("Техника пока нестабильна: исправьте ключевые ошибки до увеличения нагрузки.")

    lines.append("")
    lines.append("Топ-3 ошибки техники")

    top_issues_raw = ui_payload.get("topIssues")
    top_issues = top_issues_raw if isinstance(top_issues_raw, list) else []
    if not top_issues:
        lines.append("Критичных технических ошибок в этом логе не зафиксировано.")
    else:
        for index, issue in enumerate(top_issues[:3], start=1):
            if not isinstance(issue, dict):
                continue
            issue_code = issue.get("code")
            title = _normalize_issue_title(issue.get("title"), issue_code)
            explanation = _to_clean_text(issue.get("explanation"))
            severity = SEVERITY_LABELS.get(_to_clean_text(issue.get("severity"), fallback="med").lower(), "средний приоритет")
            evidence = _humanize_evidence_ref(issue.get("evidenceRef"))
            lines.append(f"{index}. {title} — {explanation} ({severity}).")
            lines.append(f"   Основание: {evidence}")

    lines.append("")
    lines.append("Что делать в следующем подходе")

    recommendations_raw = ui_payload.get("recommendations")
    recommendations = recommendations_raw if isinstance(recommendations_raw, list) else []
    unique_advice: set[str] = set()
    prepared_recommendations: list[dict[str, Any]] = []

    for index, issue in enumerate(top_issues[:5]):
        if not isinstance(issue, dict):
            continue

        code = _to_clean_text(issue.get("code"), fallback="")
        template = RECOMMENDATION_ACTIONS_BY_CODE.get(code)
        if template is None:
            continue

        advice = _to_clean_text(template.get("advice"), fallback="")
        if not advice:
            continue

        key = advice.lower()
        if key in unique_advice:
            continue
        unique_advice.add(key)

        steps = _format_steps(template.get("steps"))
        if len(steps) < 2:
            steps = [
                "Сделайте 2 медленных повтора и не ускоряйтесь внизу.",
                "Проверьте, что каждый следующий повтор выглядит так же, как предыдущий.",
            ]

        prepared_recommendations.append(
            {
                "advice": advice,
                "steps": steps[:4],
                "evidence": _humanize_evidence_ref(issue.get("evidenceRef") or f"ui.topIssues[{index}].code"),
            }
        )

        if len(prepared_recommendations) >= 5:
            break

    if len(prepared_recommendations) < 3:
        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
            advice = _to_clean_text(rec.get("advice"), fallback="")
            if not advice:
                continue
            key = advice.lower()
            if key in unique_advice:
                continue
            unique_advice.add(key)

            steps = _format_steps(rec.get("steps"))
            if len(steps) < 2:
                steps = [
                    "Сделайте 2 медленных повтора и не ускоряйтесь внизу.",
                    "Проверьте, что каждый следующий повтор выглядит так же, как предыдущий.",
                ]

            prepared_recommendations.append(
                {
                    "advice": advice,
                    "steps": steps[:4],
                    "evidence": _humanize_evidence_ref(rec.get("evidenceRef")),
                }
            )

            if len(prepared_recommendations) >= 5:
                break

    fallback_actions = [
        "Снизьте темп и держите одинаковую амплитуду в каждом повторе.",
        "Сделайте 2 разминочных повтора перед рабочим подходом.",
        "Остановите повтор, если теряете контроль техники.",
    ]
    for fallback_advice in fallback_actions:
        if len(prepared_recommendations) >= 3:
            break
        if fallback_advice.lower() in unique_advice:
            continue
        unique_advice.add(fallback_advice.lower())
        prepared_recommendations.append(
            {
                "advice": fallback_advice,
                "steps": [
                    "Выполняйте повторы в медленном темпе без рывков.",
                    "Сохраняйте одинаковую амплитуду и темп на протяжении подхода.",
                ],
                "evidence": "ui.summary.qualityLabel",
            }
        )

    if reps_count is not None and reps_count < 6:
        lines.append("1. Доделайте подход до рабочего объёма 6-8 повторов.")
        lines.append("   - Шаг 1: Первые 2 повтора сделайте медленно для фиксации траектории.")
        lines.append("   - Шаг 2: Ещё 2-4 повтора сделайте в том же темпе, без рывка вверх.")
        lines.append("   Основание: ui.summary.repsCount")
        start_index = 2
    else:
        start_index = 1

    if not prepared_recommendations:
        lines.append(f"{start_index}. Сохраняйте одинаковый темп и амплитуду на всех повторах.")
        lines.append("   - Шаг 1: Опускайтесь на счёт «раз-два».")
        lines.append("   - Шаг 2: Поднимайтесь без рывка, сохраняя контроль.")
        lines.append("   Основание: ui.summary.qualityLabel")
    else:
        for index, rec in enumerate(prepared_recommendations, start=start_index):
            lines.append(f"{index}. {rec['advice']}")
            for step_index, step in enumerate(rec["steps"], start=1):
                lines.append(f"   - Шаг {step_index}: {step}")
            lines.append(f"   Основание: {rec['evidence']}")

    lines.append("")
    lines.append("Риски/безопасность")

    risks_raw = ui_payload.get("risks")
    risks = risks_raw if isinstance(risks_raw, list) else []
    if not risks:
        lines.append("Критичных рисков по текущему логу не выявлено.")
    else:
        for risk in risks:
            if not isinstance(risk, dict):
                continue
            title = _to_clean_text(risk.get("title"))
            description = _to_clean_text(risk.get("description"))
            evidence = _humanize_evidence_ref(risk.get("evidenceRef"))
            lines.append(f"- {title}: {description}")
            lines.append(f"  Основание: {evidence}")

    lines.append("")
    lines.append("Фокус на следующий подход")
    focus_text = _to_clean_text(ui_payload.get("motivation"), fallback="")
    if not focus_text:
        focus_text = "Сделайте следующий подход спокойнее, но с более точной техникой."
    lines.append(focus_text)

    return "\n".join(lines).strip()


def generate_training_report_from_log(log_path: Path, user_id: int) -> TrainingReportResult:
    normalized_log_path = _normalize_log_path(log_path)
    payload = _load_log_payload(normalized_log_path, user_id=user_id)

    ui_payload = payload.get("ui")
    meta_payload = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    report_payload = payload.get("report") if isinstance(payload.get("report"), dict) else {}

    payload_text = _to_prompt_json_text(payload)
    ultra_payload_text = _to_ultra_prompt_json_text(payload)
    report_text = ""
    try:
        try:
            first_report = _generate_with_llm(payload_text, strict_retry=False)
        except ValueError as exc:
            if "exceed context window" in str(exc).lower():
                logging.warning(
                    "Контекст LLM переполнен на первом проходе. Повтор с компактным payload."
                )
                first_report = _generate_with_llm(ultra_payload_text, strict_retry=False)
            else:
                raise
        first_normalized = _normalize_report_text(first_report)
        first_valid, first_issues = _validate_report(first_normalized)

        if first_valid:
            first_final = _ensure_required_sections(first_normalized)
            if _is_low_quality_llm_report(first_final):
                logging.info("LLM-отчёт содержит слишком много заглушек. Используется fallback по ui.")
            else:
                report_text = first_final
        else:
            try:
                second_report = _generate_with_llm(payload_text, strict_retry=True)
            except ValueError as exc:
                if "exceed context window" in str(exc).lower():
                    logging.warning(
                        "Контекст LLM переполнен на повторе. Повтор с компактным payload."
                    )
                    second_report = _generate_with_llm(ultra_payload_text, strict_retry=True)
                else:
                    raise

            second_normalized = _normalize_report_text(second_report)
            second_valid, second_issues = _validate_report(second_normalized)
            if second_valid:
                second_final = _ensure_required_sections(second_normalized)
                if _is_low_quality_llm_report(second_final):
                    logging.info("LLM-отчёт после повтора остался с заглушками. Используется fallback по ui.")
                else:
                    report_text = second_final
            else:
                logging.warning(
                    "LLM-отчёт не прошёл валидацию после повтора (%s | %s). Будет fallback по ui.",
                    "; ".join(first_issues) if first_issues else "нет деталей",
                    "; ".join(second_issues) if second_issues else "нет деталей",
                )
    except Exception as exc:  # pragma: no cover - fallback path
        logging.warning("LLM-генерация недоступна, используется fallback по ui: %s", exc)

    if not report_text:
        fallback_ui = ui_payload if _has_ui_data(ui_payload) else _build_legacy_ui_fallback(payload)
        report_text = build_report_from_ui(
            ui_payload=fallback_ui,
            meta_payload=meta_payload,
            report_payload=report_payload,
        )

    if not report_text.strip():
        raise ReportGenerationError("Модель вернула пустой отчёт.")

    report_text = _sanitize_evidence_lines(report_text).strip()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{normalized_log_path.stem}_report.md"

    try:
        report_path.write_text(report_text.strip() + "\n", encoding="utf-8")
    except OSError as exc:
        raise ReportGenerationError("Не удалось сохранить сгенерированный отчёт на диск.") from exc

    return TrainingReportResult(
        report_markdown=report_text.strip(),
        report_path=report_path.resolve(),
        avg_score=_safe_avg_score(payload),
    )
