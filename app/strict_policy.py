"""最严格筛查策略（默认开启，可在 settings.json 关闭 strict_mode）。"""

from __future__ import annotations

from app.settings import get_settings


def is_strict() -> bool:
    return bool(get_settings().get("strict_mode", True))


def risk_thresholds() -> tuple[int, int]:
    """返回 (中危下限, 高危下限)。"""
    if is_strict():
        return (
            int(get_settings().get("strict_risk_mid", 30)),
            int(get_settings().get("strict_risk_high", 55)),
        )
    return (40, 70)


def risk_level_from_score(score: int) -> str:
    mid, high = risk_thresholds()
    if score >= high:
        return "高危"
    if score >= mid:
        return "中危"
    return "低危"


def weight_adjustment(base_weight: int) -> int:
    if not is_strict():
        return base_weight
    bonus = int(get_settings().get("strict_weight_bonus", 4))
    return min(45, base_weight + bonus)


def combo_bonus_adjustment(bonus: int) -> int:
    if not is_strict():
        return bonus
    mul = float(get_settings().get("strict_combo_multiplier", 1.3))
    return int(round(bonus * mul))


def score_compute_multiplier() -> float:
    if not is_strict():
        return 1.0
    return float(get_settings().get("strict_score_multiplier", 1.12))


def min_score_on_match() -> int:
    if not is_strict():
        return 0
    return int(get_settings().get("strict_min_on_match", 35))


def min_score_recruitment_text() -> int:
    """有招聘语境但规则命中少时仍抬高底线。"""
    if not is_strict():
        return 0
    return int(get_settings().get("strict_min_recruitment", 28))


def min_score_final_floor() -> int:
    if not is_strict():
        return 0
    return int(get_settings().get("strict_min_final", 22))


def biz_bonus_cap() -> int:
    return int(get_settings().get("strict_biz_bonus_cap", 45) if is_strict() else 35)


def biz_bonus_multiplier() -> float:
    return float(get_settings().get("strict_biz_multiplier", 1.25) if is_strict() else 1.0)


def ai_trigger_mode() -> str | None:
    """严格模式 AI 策略：smart | always | borderline | high_risk_only"""
    if not is_strict():
        return None
    mode = get_settings().get("strict_ai_trigger")
    if mode:
        return str(mode).strip().lower()
    return "smart"


def ai_skip_high_score() -> int:
    return int(get_settings().get("strict_ai_skip_high_score", 88))


def ai_borderline_range() -> tuple[int, int]:
    if is_strict():
        return (
            int(get_settings().get("strict_ai_borderline_min", 18)),
            int(get_settings().get("strict_ai_borderline_max", 85)),
        )
    return (35, 75)


def company_autofill_min_score() -> int:
    return int(get_settings().get("strict_company_min_score", 12) if is_strict() else 10)


def apply_strict_score_floor(text: str, score: int, match_count: int) -> int:
    if not is_strict():
        return score
    s = score
    if match_count > 0:
        s = max(s, min_score_on_match())
    elif len(text.strip()) >= 50 and any(
        k in text for k in ("招聘", "岗位", "职位", "HR", "面试", "简历", "求职")
    ):
        s = max(s, min_score_recruitment_text())
    s = max(s, min_score_final_floor())
    return min(100, s)


def recruitment_keywords_present(text: str) -> bool:
    return any(k in text for k in ("招聘", "岗位", "职位", "JD", "求职", "面试"))
