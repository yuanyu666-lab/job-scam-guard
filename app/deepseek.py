"""DeepSeek API（OpenAI 兼容）。"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from app.ai_insight import AiInsight, insight_to_dict
from app.ai_prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
    parse_json_payload,
    payload_to_insight,
)
from app.engine import AnalysisResult

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "deepseek_config.json"
API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
FALLBACK_MODELS = ("deepseek-reasoner",)


def load_config() -> dict:
    cfg: dict = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            cfg = raw
    key = (
        cfg.get("api_key")
        or os.environ.get("DEEPSEEK_API_KEY")
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


def _friendly_api_error(exc: Exception, body: str = "") -> str:
    raw = (body or str(exc)).strip()
    lower = raw.lower()
    if "insufficient" in lower or "balance" in lower or "402" in raw:
        return "DeepSeek 账户余额不足，请在 platform.deepseek.com 充值。"
    if "401" in raw or "authentication" in lower:
        return "DeepSeek API Key 无效，请检查 deepseek_config.json。"
    if "429" in raw or "rate" in lower:
        return f"DeepSeek 请求过快或限流，请稍后再试。{raw[:160]}"
    return raw[:240] + ("…" if len(raw) > 240 else "")


def _post_chat(api_key: str, model: str, user_prompt: str, timeout: int) -> str:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT + "\n请用 json 格式输出。",
            },
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 1024,
        "stream": False,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("DeepSeek 返回空 choices")
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    if not str(content).strip():
        raise RuntimeError("DeepSeek 返回空内容")
    return str(content)


def analyze_with_deepseek(
    text: str,
    content_type: str,
    rule: AnalysisResult,
) -> AiInsight:
    cfg = load_config()
    api_key = (cfg.get("api_key") or "").strip()
    if not api_key:
        return AiInsight(ok=False, provider="deepseek", error="未配置 DeepSeek API Key")
    if cfg.get("enabled") is False:
        return AiInsight(ok=False, provider="deepseek", error="DeepSeek 已在配置中关闭")

    timeout = int(cfg.get("timeout_seconds") or 60)
    models_to_try = [_resolve_model(cfg)]
    if _allow_fallback(cfg):
        for fb in FALLBACK_MODELS:
            if fb not in models_to_try:
                models_to_try.append(fb)

    user_prompt = build_user_prompt(text, content_type, rule)
    errors: list[str] = []
    retries = _max_retries(cfg)

    for model in models_to_try:
        for attempt in range(retries + 1):
            try:
                raw = _post_chat(api_key, model, user_prompt, timeout)
                data = parse_json_payload(raw)
                if not data:
                    errors.append(f"{model}: 无法解析 JSON 响应")
                    break
                insight = payload_to_insight(data, provider="deepseek", model=model)
                return insight
            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", errors="replace")
                except Exception:
                    pass
                msg = _friendly_api_error(e, body)
                is_429 = e.code == 429
                if is_429 and attempt < retries:
                    time.sleep(2**attempt + 1)
                    continue
                errors.append(f"{model}: {msg}")
                break
            except Exception as e:
                msg = _friendly_api_error(e)
                is_429 = "429" in str(e)
                if is_429 and attempt < retries:
                    time.sleep(2**attempt + 1)
                    continue
                errors.append(f"{model}: {msg}")
                break

    if errors:
        tried = " → ".join(models_to_try)
        return AiInsight(
            ok=False,
            provider="deepseek",
            error=f"已依次尝试 [{tried}]，均未成功。{'; '.join(errors)}",
        )
    return AiInsight(ok=False, provider="deepseek", error="DeepSeek 调用失败")
