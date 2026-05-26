"""从粘贴文本解析工商信息、行业信号，补充招聘风险（不替代天眼查）。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from app.biz_summary import parse_biz_summary
from app.engine import AnalysisResult, MatchDetail
from app.strict_policy import (
    biz_bonus_cap,
    biz_bonus_multiplier,
    is_strict,
    risk_level_from_score,
)


@dataclass
class BizRiskResult:
    warnings: list[str] = field(default_factory=list)
    score_bonus: int = 0
    registered_capital_wan: float | None = None
    establish_date: str | None = None
    company_type: str | None = None
    summary_parse: dict | None = None

    def to_dict(self) -> dict:
        d = {
            "warnings": self.warnings,
            "score_bonus": self.score_bonus,
            "registered_capital_wan": self.registered_capital_wan,
            "establish_date": self.establish_date,
            "company_type": self.company_type,
        }
        if self.summary_parse:
            d["summary_parse"] = self.summary_parse
        return d


_CAPITAL_RE = re.compile(
    r"(?:注册资金|注册资本)[:：]?\s*(\d+(?:\.\d+)?)\s*万",
    re.IGNORECASE,
)
_ESTABLISH_RE = re.compile(
    r"(?:成立日期|成立时间|注册日期)[:：]?\s*(\d{4})[年\-/.](\d{1,2})[月\-/.](\d{1,2})",
)
_COMPANY_TYPE_RE = re.compile(
    r"企业类型[:：]?\s*([^\n,，。；;]{4,40})"
)
_LARGE_CLAIM_RE = re.compile(
    r"(大型|龙头|知名|领先|头部)(?:私域|电商|公司|企业|团队)?"
)

_INDUSTRY_RISKY = (
    "私域电商",
    "私域",
    "复制粘贴",
    "线上运营团队",
    "有手机就能",
    "日结",
    "居家办公",
    "不用坐班",
)


def _parse_capital_wan(text: str) -> float | None:
    m = _CAPITAL_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _parse_establish(text: str) -> date | None:
    m = _ESTABLISH_RE.search(text)
    if not m:
        return None
    try:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(y, mo, d)
    except ValueError:
        return None


def _months_since(d: date) -> int:
    today = date.today()
    return (today.year - d.year) * 12 + today.month - d.month


def analyze_biz_risk(text: str) -> BizRiskResult:
    """解析文本中的工商字段与高风险行业描述。"""
    out = BizRiskResult()
    cap = _parse_capital_wan(text)
    if cap is not None:
        out.registered_capital_wan = cap
        if cap < 10:
            out.warnings.append(f"注册资本仅 {cap:g} 万元，空壳/皮包公司风险高")
            out.score_bonus += 22
        elif cap < 50:
            out.warnings.append(f"注册资本 {cap:g} 万元偏低，与大规模招聘描述可能不符")
            out.score_bonus += 16
        elif cap < 100:
            out.warnings.append(f"注册资本 {cap:g} 万元不高，建议核实实缴与参保人数")
            out.score_bonus += 10
        elif is_strict() and cap < 200:
            out.warnings.append(f"注册资本 {cap:g} 万元，严格模式下建议重点核实实缴与参保")
            out.score_bonus += 5

    est = _parse_establish(text)
    if est:
        out.establish_date = est.isoformat()
        months = _months_since(est)
        if est > date.today():
            out.warnings.append(f"成立日期 {est} 在未来，数据异常，高度可疑")
            out.score_bonus += 20
        elif months < 12:
            out.warnings.append(f"成立不足 1 年（{est}），初创公司履约与社保风险较高")
            out.score_bonus += 18
        elif months < 36:
            out.warnings.append(f"成立约 {months} 个月，仍属新设主体，建议查参保与实缴")
            out.score_bonus += 12

    tm = _COMPANY_TYPE_RE.search(text)
    if tm:
        ctype = tm.group(1).strip()
        out.company_type = ctype
        if "自然人独资" in ctype or "一人有限" in ctype:
            out.warnings.append("企业类型为自然人独资，责任有限、跑路成本较低")
            out.score_bonus += 8

    if _LARGE_CLAIM_RE.search(text) and cap is not None and cap < 200:
        out.warnings.append("自称「大型/头部」但注册资本不高，宣传与工商信息不一致")
        out.score_bonus += 10

    industry_hits = [k for k in _INDUSTRY_RISKY if k in text]
    if "私域" in text and any(k in text for k in ("复制粘贴", "复制", "粘贴", "文案", "抖音", "微信")):
        out.warnings.append("私域电商 + 复制粘贴/站外发文案，常见引流或灰产运营岗")
        out.score_bonus += 14
    elif "私域" in text or "私域电商" in text:
        out.warnings.append("私域电商岗位波动大，需核实真实业务与劳动合同")
        out.score_bonus += 12
    else:
        other_hits = [k for k in _INDUSTRY_RISKY if k in text and k not in ("私域", "私域电商")]
        if other_hits:
            kw = other_hits[0]
            out.warnings.append(f"出现高风险行业/岗位描述「{kw}」，建议重点核实")
            out.score_bonus += 6

    summary = parse_biz_summary(text)
    if summary.warnings:
        for w in summary.warnings:
            if w not in out.warnings:
                out.warnings.append(w)
        out.score_bonus += summary.score_bonus
        out.summary_parse = summary.to_dict()

    if "参保" in text and any(
        x in text for x in ("0人", "未参保", "暂无参保", "参保人数为0", "参保人数：0")
    ):
        out.warnings.append("文本显示参保人数为 0 或未参保，用工风险极高")
        out.score_bonus += 16

    # 未写薪资结构但强调轻松/福利
    if any(k in text for k in ("工作轻松", "带薪休假", "福利", "冬暖夏凉")) and not re.search(
        r"(?:薪资|工资|月薪|底薪|\d{3,}\s*元|k/月|K/月)", text, re.I
    ):
        if not any(w for w in out.warnings if "薪资" in w):
            out.warnings.append("强调福利/轻松但未写薪资结构，需面试追问")
            out.score_bonus += 6

    mul = biz_bonus_multiplier()
    if mul != 1.0:
        out.score_bonus = int(round(out.score_bonus * mul))
    out.score_bonus = min(biz_bonus_cap(), out.score_bonus)
    return out


def apply_biz_risk(rule: AnalysisResult, biz: BizRiskResult) -> AnalysisResult:
    """把工商/经营风险并入规则结果。"""
    if not biz.warnings and biz.score_bonus <= 0:
        return rule

    matches = list(rule.matches)
    if biz.warnings:
        matches.append(
            MatchDetail(
                category_id="biz_risk",
                category_name="工商/经营信号",
                weight=min(28, 12 + biz.score_bonus // 2),
                hits=biz.warnings[:6],
            )
        )

    new_score = min(100, rule.risk_score + biz.score_bonus)
    suggestions = list(rule.suggestions)
    for w in biz.warnings[:4]:
        tip = f"【工商】{w}"
        if tip not in suggestions:
            suggestions.insert(0, tip)

    return AnalysisResult(
        risk_score=new_score,
        risk_level=risk_level_from_score(new_score),
        matches=matches,
        suggestions=suggestions,
        highlight_terms=rule.highlight_terms,
        urls_found=rule.urls_found,
        url_warnings=rule.url_warnings,
    )
