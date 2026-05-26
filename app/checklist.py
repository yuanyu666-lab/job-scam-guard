"""企业核查清单（可复制到剪贴板）。"""

from __future__ import annotations

from app.company import extract_company_names


def build_verification_checklist(text: str, result: dict | None = None) -> str:
    result = result or {}
    names = extract_company_names(text)
    company = names[0] if names else "（请填写公司全称）"
    level = result.get("risk_level_display") or result.get("risk_level") or "—"
    score = result.get("risk_score", "—")

    lines = [
        f"【招聘防骗 · 企业核查清单】",
        f"公司：{company}",
        f"本工具结论：{level}（{score} 分，仅供参考）",
        "",
        "□ 国家企业信用公示系统：存续/在业",
        "□ 注册资本 vs 实缴资本（认缴≠实缴）",
        "□ 最新年报参保人数（是否 0～2 人却大量招聘）",
        "□ 成立时间是否过新、是否自然人独资",
        "□ 经营异常、失信、被执行人、限制高消费",
        "□ 合同甲方、办公地址、社保缴纳月、底薪与提成（书面）",
        "□ 拒绝：先交钱、培训贷、私人微信单聊、不明 App、刷单垫付",
    ]

    biz = result.get("biz_warnings") or []
    if biz:
        lines.extend(["", "【本工具已提示的工商/经营信号】"])
        for w in biz[:8]:
            lines.append(f"  · {w}")

    headline = result.get("headline")
    if headline:
        lines.extend(["", f"结论：{headline}"])

    lines.extend(["", "— 由 job-scam-guard 生成，非法律意见 —"])
    return "\n".join(lines)
