"""Gemini 大模型增强分析（可选，需 API Key）。"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from app.ai_insight import AiInsight
from app.ai_prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
    parse_json_payload,
    payload_to_insight,
)
from app.engine import AnalysisResult

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "gemini_config.json"

DEFAULT_MODEL = "gemini-3.1-pro-preview"
FALLBACK_MODELS = ("gemini-3.1-flash-preview", "gemini-2.5-flash")


def load_config() -> dict:
    cfg: dict = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            cfg = raw
    key = (
        cfg.get("api_key")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or ""
    ).strip()
    if key:
        cfg["api_key"] = key
    return cfg


def is_configured() -> bool:
    cfg = load_config()
    if cfg.get("enabled") is False:
        return False
    return bool((cfg.get("api_key") or "").strip())


def _resolve_model(cfg: dict) -> str:
    return (cfg.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _allow_fallback(cfg: dict) -> bool:
    return bool(cfg.get("allow_fallback", False))


def _max_retries(cfg: dict) -> int:
    return max(0, min(5, int(cfg.get("retry_on_429") or 2)))


def _friendly_api_error(exc: Exception) -> str:
    raw = str(exc).strip()
    lower = raw.lower()
    if "free_tier" in lower or "free tier" in lower:
        return (
            "API Key 仍在免费层配额（与 gemini.google.com 的 Pro 会员不是同一套）。"
            "请到 AI Studio → Billing 为该项目开通计费，并在计费生效后重新生成 Key。"
        )
    if "spending cap" in lower or "monthly spending" in lower:
        return "已达到 AI Studio 项目/账单月度支出上限，请在 Billing 里调高 Spend Cap。"
    if "429" in raw or "resource_exhausted" in lower:
        return f"请求过快或配额用尽（429），请稍等 1 分钟再试。详情: {raw[:200]}"
    return raw[:240] + ("…" if len(raw) > 240 else "")


def analyze_with_gemini(
    text: str,
    content_type: str,
    rule: AnalysisResult,
) -> AiInsight:
    cfg = load_config()
    api_key = (cfg.get("api_key") or "").strip()
    if not api_key:
        return AiInsight(ok=False, provider="gemini", error="未配置 Gemini API Key")
    if cfg.get("enabled") is False:
        return AiInsight(ok=False, provider="gemini", error="Gemini 已在配置中关闭")

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return AiInsight(
            ok=False,
            provider="gemini",
            error="未安装 google-genai，请执行: pip install google-genai",
        )

    models_to_try = [_resolve_model(cfg)]
    if _allow_fallback(cfg):
        for fb in FALLBACK_MODELS:
            if fb not in models_to_try:
                models_to_try.append(fb)

    client = genai.Client(api_key=api_key)
    user_prompt = build_user_prompt(text, content_type, rule)
    errors: list[str] = []
    retries = _max_retries(cfg)

    for model in models_to_try:
        for attempt in range(retries + 1):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.2,
                        max_output_tokens=1024,
                        response_mime_type="application/json",
                    ),
                )
                raw = (response.text or "").strip()
                data = parse_json_payload(raw)
                if not data:
                    errors.append(f"{model}: 无法解析 JSON 响应")
                    break
                return payload_to_insight(data, provider="gemini", model=model)
            except Exception as e:
                msg = _friendly_api_error(e)
                is_429 = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
                if is_429 and attempt < retries:
                    time.sleep(2**attempt + 1)
                    continue
                errors.append(f"{model}: {msg}")
                break

    if errors:
        tried = " → ".join(models_to_try)
        return AiInsight(
            ok=False,
            provider="gemini",
            error=f"已依次尝试 [{tried}]，均未成功。{'; '.join(errors)}",
        )
    return AiInsight(ok=False, provider="gemini", error="Gemini 调用失败")
