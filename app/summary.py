"""生成人话结论与行动建议。"""

from __future__ import annotations

from app.strict_policy import is_strict, risk_thresholds

# 界面展示（严格模式更冷）
LEVEL_DISPLAY = {
    "高危": "高危",
    "中危": "可疑",
    "低危": "警惕",
    "失败": "识别失败",
}

LEVEL_DISPLAY_RELAXED = {
    "高危": "高危",
    "中危": "可疑",
    "低危": "待核实",
    "失败": "识别失败",
}


def display_risk_level(level: str) -> str:
    mapping = LEVEL_DISPLAY if is_strict() else LEVEL_DISPLAY_RELAXED
    return mapping.get(level, level)


def _base_headline(score: int, level: str, biz_warnings: list[str]) -> str:
    mid, high = risk_thresholds()
    if score >= high or level == "高危":
        return "高度可疑，建议立即停止沟通"
    if score >= mid or level == "中危":
        return "存在可疑信号，不建议贸然入职"
    if biz_warnings:
        return "话术未命中典型骗局，但工商/经营信号偏多"
    if is_strict():
        return "严格模式：未发现典型诈骗话术，仍建议全面核实后再决定"
    return "话术暂未命中骗局特征，仍须核实企业与合同"


def _base_actions(score: int, level: str, biz_warnings: list[str]) -> list[str]:
    mid, high = risk_thresholds()
    if score >= high or level == "高危":
        return [
            "不要转账、出借账户或先交任何费用",
            "保留聊天记录/截图，向平台举报或报警",
        ]
    if score >= mid or level == "中危":
        actions = [
            "天眼查/企查查：实缴资本、参保人数、经营异常、司法风险",
            "书面确认合同主体、社保缴纳月、底薪与提成，拒绝私人微信单聊",
        ]
        if biz_warnings:
            actions.append("新设/小资本/独资公司优先避开或仅作备选")
        return actions[:2]

    actions = []
    if biz_warnings or is_strict():
        actions.append("天眼查/企查查：实缴、参保、成立时间、司法与经营异常")
        actions.append("面试清单：合同谁签、社保何时缴、底薪提成、办公地址实地看")
    else:
        actions.append("核对公司全称、招聘邮箱域名是否与官网一致")
        actions.append("警惕后续要求转账、培训费或加私人联系方式")
    return actions[:2]


def enrich_result(
    result: dict,
    *,
    content_type: str,
    content_label: str,
    biz_warnings: list[str] | None = None,
) -> dict:
    biz_warnings = biz_warnings or result.get("biz_warnings") or []
    score = int(result.get("risk_score") or 0)
    level = result.get("risk_level") or "低危"
    headline = _base_headline(score, level, biz_warnings)
    actions = _base_actions(score, level, biz_warnings)

    ai = result.get("ai") or {}
    if ai.get("ok") and ai.get("summary"):
        summary = str(ai["summary"]).strip()
        if summary and len(summary) <= 120:
            headline = summary
        elif summary:
            headline = summary[:117] + "…"

    for tip in ai.get("advice") or []:
        if tip and tip not in actions and len(actions) < 2:
            actions.append(str(tip).strip())

    for s in result.get("suggestions") or []:
        s = str(s).strip()
        if not s or s.startswith("【"):
            continue
        if s not in actions and len(actions) < 2:
            actions.append(s)

    result["headline"] = headline
    result["actions"] = actions[:2]
    result["content_type"] = content_type
    result["content_type_label"] = content_label
    result["risk_level_display"] = display_risk_level(level)
    result["strict_mode"] = is_strict()
    return result
