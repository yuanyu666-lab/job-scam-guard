"""命中明细与分数构成说明。"""

from __future__ import annotations

from app.engine import AnalysisResult


def build_score_breakdown(
    rule: AnalysisResult,
    *,
    biz_bonus: int = 0,
    strict_floor_applied: int | None = None,
) -> list[dict]:
    items: list[dict] = []
    for m in rule.matches:
        items.append(
            {
                "kind": "rule",
                "id": m.category_id,
                "name": m.category_name,
                "weight": m.weight,
                "detail": (m.hits[0] if m.hits else "")[:80],
            }
        )
    if biz_bonus > 0:
        items.append(
            {
                "kind": "biz",
                "id": "biz_risk",
                "name": "工商/经营信号加成",
                "weight": biz_bonus,
                "detail": f"+{biz_bonus} 分",
            }
        )
    if rule.url_warnings:
        items.append(
            {
                "kind": "url",
                "id": "url",
                "name": "可疑链接",
                "weight": min(18, len(rule.url_warnings) * 9),
                "detail": rule.url_warnings[0][:80],
            }
        )
    if strict_floor_applied is not None and strict_floor_applied > 0:
        items.append(
            {
                "kind": "floor",
                "id": "strict_floor",
                "name": "严格模式保底分",
                "weight": strict_floor_applied,
                "detail": "未达阈值时抬升",
            }
        )
    items.sort(key=lambda x: int(x.get("weight") or 0), reverse=True)
    return items


def format_breakdown_text(breakdown: list[dict], score: int, level: str) -> str:
    lines = [f"【评分明细】综合 {score} 分 · {level}"]
    for i, it in enumerate(breakdown[:12], 1):
        w = it.get("weight", 0)
        name = it.get("name", "")
        detail = it.get("detail", "")
        lines.append(f"  {i}. {name}（权重/加成 {w}）{(' · ' + detail) if detail else ''}")
    if len(breakdown) > 12:
        lines.append(f"  … 另有 {len(breakdown) - 12} 项")
    return "\n".join(lines)
