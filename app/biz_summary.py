"""解析天眼查/企查查等粘贴摘要中的结构化工商字段。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class BizSummaryParse:
    warnings: list[str] = field(default_factory=list)
    score_bonus: int = 0
    social_staff_num: int | None = None
    actual_capital_wan: float | None = None
    abnormal_count: int = 0
    legal_risk_hits: list[str] = field(default_factory=list)
    source: str = "paste"

    def to_dict(self) -> dict:
        return {
            "warnings": self.warnings,
            "score_bonus": self.score_bonus,
            "social_staff_num": self.social_staff_num,
            "actual_capital_wan": self.actual_capital_wan,
            "abnormal_count": self.abnormal_count,
            "legal_risk_hits": self.legal_risk_hits,
            "source": self.source,
        }


_SOCIAL_RE = [
    re.compile(r"(?:参保人数|社保人数|城镇职工基本养老保险)[：:\s]*(\d+)\s*人"),
    re.compile(r"参保\s*(\d+)\s*人"),
    re.compile(r"(\d+)\s*人参保"),
]
_ACTUAL_CAP_RE = [
    re.compile(r"(?:实缴资本|实缴)[：:\s]*(\d+(?:\.\d+)?)\s*万"),
    re.compile(r"实缴(?:出资)?[：:\s]*(?:人民币)?\s*(\d+(?:\.\d+)?)\s*万"),
]
_ABNORMAL_RE = re.compile(r"(?:经营异常|列入异常|异常名录)")
_LEGAL_RE = [
    ("失信被执行人", 18),
    ("被执行人", 14),
    ("限制高消费", 12),
    ("司法拍卖", 10),
    ("开庭公告", 6),
    ("法律诉讼", 8),
    ("行政处罚", 10),
]
_STATUS_BAD = [
    ("吊销", 25),
    ("注销", 20),
    ("停业", 15),
    ("清算", 15),
]


def _looks_like_platform_summary(text: str) -> bool:
    markers = (
        "天眼查",
        "企查查",
        "爱企查",
        "参保人数",
        "实缴资本",
        "经营异常",
        "统一社会信用",
        "法定代表人",
        "注册资本",
    )
    return sum(1 for m in markers if m in text) >= 2


def parse_biz_summary(text: str) -> BizSummaryParse:
    out = BizSummaryParse()
    if not _looks_like_platform_summary(text):
        return out

    out.source = "tianyancha/qcc_paste"

    for pat in _SOCIAL_RE:
        m = pat.search(text)
        if m:
            try:
                n = int(m.group(1))
            except ValueError:
                continue
            out.social_staff_num = n
            if n == 0:
                out.warnings.append("摘要显示参保人数为 0，用工风险极高")
                out.score_bonus += 20
            elif n <= 2:
                out.warnings.append(f"摘要显示参保仅 {n} 人，与大规模招聘可能不符")
                out.score_bonus += 14
            elif n <= 5:
                out.warnings.append(f"参保人数 {n} 人偏少，建议对照最新年报")
                out.score_bonus += 8
            break

    for pat in _ACTUAL_CAP_RE:
        m = pat.search(text)
        if m:
            try:
                ac = float(m.group(1))
            except ValueError:
                continue
            out.actual_capital_wan = ac
            if ac == 0:
                out.warnings.append("实缴资本为 0 或未公示，空壳风险高")
                out.score_bonus += 18
            elif ac < 10:
                out.warnings.append(f"实缴资本仅 {ac:g} 万元，与宣传规模可能不符")
                out.score_bonus += 12
            break

    if _ABNORMAL_RE.search(text):
        cnt = len(_ABNORMAL_RE.findall(text))
        out.abnormal_count = max(1, cnt)
        out.warnings.append("存在经营异常/异常名录记录")
        out.score_bonus += 16

    for kw, bonus in _LEGAL_RE:
        if kw in text:
            out.legal_risk_hits.append(kw)
            out.warnings.append(f"摘要含「{kw}」，司法/合规风险需人工核实")
            out.score_bonus += bonus

    for kw, bonus in _STATUS_BAD:
        if kw in text and any(
            x in text for x in ("经营状态", "登记状态", "企业状态", "状态")
        ):
            out.warnings.append(f"登记状态含「{kw}」，不宜入职")
            out.score_bonus += bonus
            break

    if "0人" in text and "参保" in text:
        if not any("参保" in w for w in out.warnings):
            out.warnings.append("文本含「0人参保」类描述")
            out.score_bonus += 16

    return out
