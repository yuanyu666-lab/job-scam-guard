"""选择 Gemini / DeepSeek 并统一调用。"""



from __future__ import annotations



import json

from pathlib import Path



from app.ai_insight import AiInsight

from app.engine import AnalysisResult

from app.strict_policy import (

    ai_borderline_range,

    ai_skip_high_score,

    ai_trigger_mode,

    is_strict,

    risk_thresholds,

)



AI_CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "ai_config.json"





def load_ai_config() -> dict:

    if not AI_CONFIG_PATH.exists():

        return {}

    with open(AI_CONFIG_PATH, encoding="utf-8") as f:

        raw = json.load(f)

    return raw if isinstance(raw, dict) else {}





def resolve_provider(explicit: str | None = None) -> str:

    if explicit and explicit in ("gemini", "deepseek", "none"):

        return explicit

    cfg = load_ai_config()

    p = (cfg.get("provider") or "deepseek").strip().lower()

    if p in ("gemini", "deepseek"):

        return p

    return "none"





def is_provider_configured(provider: str) -> bool:

    if provider == "gemini":

        from app.gemini import is_configured



        return is_configured()

    if provider == "deepseek":

        from app.deepseek import is_configured



        return is_configured()

    return False





def should_use_cloud_ai(use_ai: bool | None = None, provider: str | None = None) -> bool:

    if use_ai is False:

        return False

    p = resolve_provider(provider)

    if p == "none":

        return False

    if use_ai is True:

        return is_provider_configured(p)

    if not is_provider_configured(p):

        return False

    if p == "gemini":

        from app.gemini import load_config



        return bool(load_config().get("use_on_analyze", True))

    from app.deepseek import load_config



    return bool(load_config().get("use_on_analyze", True))





def _provider_config(provider: str) -> dict:

    if provider == "gemini":

        from app.gemini import load_config



        return load_config()

    from app.deepseek import load_config



    return load_config()





def _resolve_trigger(scfg: dict, cfg: dict) -> str:

    strict_trigger = ai_trigger_mode()

    return (

        strict_trigger

        or scfg.get("ai_trigger")

        or cfg.get("ai_trigger")

        or "borderline"

    ).strip().lower()





def should_call_ai_for_rule(

    rule: AnalysisResult,

    *,

    use_ai: bool | None = None,

    provider: str | None = None,

    biz_score_bonus: int = 0,

) -> tuple[bool, str | None]:

    p = resolve_provider(provider)

    if not should_use_cloud_ai(use_ai, p):

        return False, None



    cfg = _provider_config(p)

    label = "DeepSeek" if p == "deepseek" else "Gemini"

    try:

        from app.settings import get_settings



        scfg = get_settings()

    except ImportError:

        scfg = {}



    trigger = _resolve_trigger(scfg, cfg)

    score = rule.risk_score

    mid, high = risk_thresholds()

    skip_high = int(

        scfg.get("ai_skip_score_high")

        if scfg.get("ai_skip_score_high") is not None

        else ai_skip_high_score()

    )



    if score >= skip_high and rule.risk_level == "高危":

        return (

            False,

            f"本地已高危 {score} 分，结论明确，为省额度未调用 {label}",

        )



    if trigger == "always":

        return True, None



    if trigger == "high_risk_only":

        if score >= mid or biz_score_bonus >= 8:

            return True, None

        return (

            False,

            f"策略「仅高危复核」：{score} 分未达中危线，未调用 {label}",

        )



    if trigger == "smart":

        lo, hi = ai_borderline_range()

        if score < lo and biz_score_bonus < 8:

            return (

                False,

                f"智能模式：{score} 分且工商加成低，未调用 {label}",

            )

        if score > hi and biz_score_bonus < 5:

            return (

                False,

                f"智能模式：{score} 分已较明确，未调用 {label}",

            )

        return True, None



    if trigger != "borderline":

        return True, None



    lo, hi = ai_borderline_range() if is_strict() else (

        int(scfg.get("borderline_min") or cfg.get("borderline_min", 35)),

        int(scfg.get("borderline_max") or cfg.get("borderline_max", 75)),

    )



    if score < lo:

        if biz_score_bonus >= 8:

            return True, None

        return (

            False,

            f"话术 {rule.risk_level} {score} 分偏低，未调用 {label}",

        )

    if score > hi:

        if is_strict() and biz_score_bonus >= 5:

            return True, None

        return (

            False,

            f"规则已 {rule.risk_level} {score} 分，未调用 {label}",

        )

    return True, None





def analyze_with_cloud(

    text: str,

    content_type: str,

    rule: AnalysisResult,

    *,

    provider: str | None = None,

) -> AiInsight:

    p = resolve_provider(provider)

    if p == "gemini":

        from app.gemini import analyze_with_gemini



        return analyze_with_gemini(text, content_type, rule)

    if p == "deepseek":

        from app.deepseek import analyze_with_deepseek



        return analyze_with_deepseek(text, content_type, rule)

    return AiInsight(ok=False, error="未选择云端 AI 提供商")

