"""集中配置：UI 状态、OCR 偏好、AI 触发等（兼容旧 json）。"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT / "data" / "settings.json"

DEFAULTS: dict = {
    "auto_content_type": True,
    "ocr_engine": "fast",
    "ocr_min_chars": 12,
    "remember_window_position": True,
    "history_max": 10,
    "strict_mode": True,
    "strict_risk_mid": 30,
    "strict_risk_high": 55,
    "strict_min_on_match": 35,
    "strict_min_recruitment": 28,
    "strict_min_final": 22,
    "strict_weight_bonus": 4,
    "strict_combo_multiplier": 1.3,
    "strict_score_multiplier": 1.12,
    "strict_biz_multiplier": 1.25,
    "strict_biz_bonus_cap": 45,
    "strict_ai_trigger": "smart",
    "strict_ai_skip_high_score": 88,
    "ai_skip_score_high": 88,
    "save_history": True,
    "ocr_post_fix": True,
    "enabled_platform_packs": ["boss", "zhilian", "wechat"],
    "strict_ai_borderline_min": 18,
    "strict_ai_borderline_max": 85,
    "strict_company_min_score": 12,
    "ai_trigger": None,
    "borderline_min": None,
    "borderline_max": None,
    "ui": {"x": None, "y": None, "mode": "ball"},
}


def _deep_merge(base: dict, patch: dict) -> dict:
    out = deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def get_settings() -> dict:
    cfg = deepcopy(DEFAULTS)
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH, encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                cfg = _deep_merge(cfg, raw)
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_settings_patch(patch: dict) -> dict:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged = _deep_merge(get_settings(), patch)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged


def save_ui_state(*, x: int, y: int, mode: str) -> None:
    if not get_settings().get("remember_window_position", True):
        return
    save_settings_patch({"ui": {"x": x, "y": y, "mode": mode}})


def get_ui_geometry() -> tuple[int | None, int | None, str]:
    ui = get_settings().get("ui") or {}
    return ui.get("x"), ui.get("y"), ui.get("mode") or "ball"


def get_ocr_engine_pref() -> str:
    """settings 优先，其次 ocr_config.json。"""
    s = get_settings().get("ocr_engine")
    if s:
        return str(s).lower()
    ocr_path = ROOT / "data" / "ocr_config.json"
    if ocr_path.exists():
        try:
            with open(ocr_path, encoding="utf-8") as f:
                return (json.load(f).get("engine") or "auto").lower()
        except (json.JSONDecodeError, OSError):
            pass
    return "auto"
