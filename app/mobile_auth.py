"""手机端调用云端 API 的简单鉴权（可选）。"""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "mobile_api.json"


def load_mobile_api_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        return raw if isinstance(raw, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def mobile_api_enabled() -> bool:
    token = (load_mobile_api_config().get("api_token") or "").strip()
    return bool(token and token != "在此填写手机端 API Token")


def verify_api_key(header_value: str | None) -> None:
    """未配置 token 时不校验；已配置则必须匹配。"""
    if not mobile_api_enabled():
        return
    expected = (load_mobile_api_config().get("api_token") or "").strip()
    got = (header_value or "").strip()
    if got != expected:
        from fastapi import HTTPException

        raise HTTPException(401, "API Key 无效")
