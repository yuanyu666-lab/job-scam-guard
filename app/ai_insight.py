"""云端 AI 分析结果（Gemini / DeepSeek 共用）。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AiInsight:
    ok: bool
    provider: str = ""
    risk_score: int | None = None
    risk_level: str | None = None
    summary: str = ""
    scam_types: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    advice: list[str] = field(default_factory=list)
    confidence: str | None = None
    model: str = ""
    error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None


def insight_to_dict(insight: AiInsight) -> dict:
    return {
        "ok": insight.ok,
        "provider": insight.provider,
        "risk_score": insight.risk_score,
        "risk_level": insight.risk_level,
        "summary": insight.summary,
        "scam_types": insight.scam_types,
        "red_flags": insight.red_flags,
        "advice": insight.advice,
        "confidence": insight.confidence,
        "model": insight.model,
        "error": insight.error,
        "skipped": insight.skipped,
        "skip_reason": insight.skip_reason,
    }
