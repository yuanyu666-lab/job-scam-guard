"""合并本地规则与云端 AI 结果。"""

from __future__ import annotations

from app.ai_insight import AiInsight, insight_to_dict
from app.engine import AnalysisResult
from app.ai_prompt import normalize_level


def merge_rule_and_ai(rule: AnalysisResult, ai: AiInsight | None) -> dict:
    base = {
        "risk_score": rule.risk_score,
        "risk_level": rule.risk_level,
        "matches": [
            {
                "category_id": m.category_id,
                "category_name": m.category_name,
                "weight": m.weight,
                "hits": m.hits,
            }
            for m in rule.matches
        ],
        "suggestions": list(rule.suggestions),
        "highlight_terms": rule.highlight_terms,
        "urls_found": rule.urls_found,
        "url_warnings": rule.url_warnings,
        "rule_score": rule.risk_score,
        "rule_level": rule.risk_level,
    }

    if ai is None:
        base["ai"] = {"used": False, "configured": False}
        return base

    from app.ai_router import is_provider_configured, resolve_provider

    provider = ai.provider or resolve_provider()
    ai_block = {
        "configured": is_provider_configured(provider),
        "used": True,
        "provider": provider,
        **insight_to_dict(ai),
    }
    base["ai"] = ai_block

    if ai.ok and ai.risk_score is not None:
        merged = max(rule.risk_score, ai.risk_score)
        base["risk_score"] = merged
        base["risk_level"] = normalize_level(
            ai.risk_level if ai.risk_score >= rule.risk_score else rule.risk_level,
            merged,
        )
        label = "DeepSeek" if provider == "deepseek" else "Gemini"
        extra: list[str] = []
        if ai.summary:
            extra.append(f"【{label}】{ai.summary}")
        for tip in ai.advice[:3]:
            if tip and tip not in base["suggestions"]:
                extra.append(tip)
        base["suggestions"] = extra + base["suggestions"]

    return base
