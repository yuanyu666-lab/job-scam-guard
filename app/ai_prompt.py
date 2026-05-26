"""云端 AI 共用提示词与解析。"""

from __future__ import annotations

import json
import re

from app.engine import AnalysisResult

SYSTEM_PROMPT = """你是招聘诈骗识别助手，面向中国求职者。
根据用户提供的招聘话术、职位描述或聊天记录，判断是否存在诈骗或高风险信号。

常见类型：刷单返利、招转培、帮信洗钱、虚假 offer、打字/文员诱饵、收割年轻人、
付费内推、传销式招聘、先交钱后入职、要求两部手机/出借银行卡、非官方域名等。

你必须只输出一个 JSON 对象，不要 markdown 代码块，不要其它文字。字段：
- risk_score: 0-100 整数
- risk_level: 只能是「低危」「中危」「高危」
- summary: 一两句话结论（中文）
- scam_types: 字符串数组，疑似骗局类型，无则 []
- red_flags: 字符串数组，具体可疑点，最多 6 条
- advice: 字符串数组，给求职者的建议，最多 4 条
- confidence: high / medium / low

评分参考：明显刷单/转账/帮信 → 85+；年轻人群+空洞高薪文员 → 70+；
仅有轻微营销话术 → 40 以下。"""


def build_user_prompt(text: str, content_type: str, rule: AnalysisResult) -> str:
    rule_lines = []
    for m in rule.matches[:8]:
        hits = "；".join(m.hits[:3]) if m.hits else ""
        rule_lines.append(f"- {m.category_name}（权重{m.weight}）{hits}")
    rule_block = "\n".join(rule_lines) if rule_lines else "- 未命中本地规则"
    type_label = {"job": "职位描述", "chat": "聊天记录", "general": "通用文本"}.get(
        content_type, "通用文本"
    )
    return (
        f"内容类型：{type_label}\n"
        f"本地规则引擎评分：{rule.risk_score}（{rule.risk_level}）\n"
        f"本地命中项：\n{rule_block}\n\n"
        f"待分析正文：\n{text[:12000]}"
    )


def parse_json_payload(text: str) -> dict | None:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


def normalize_level(level: str | None, score: int) -> str:
    if level in ("低危", "中危", "高危"):
        return level
    if score >= 70:
        return "高危"
    if score >= 40:
        return "中危"
    return "低危"


def payload_to_insight(data: dict, *, provider: str, model: str) -> AiInsight:
    from app.ai_insight import AiInsight

    score = int(data.get("risk_score", 0))
    score = max(0, min(100, score))
    level = normalize_level(data.get("risk_level"), score)

    def _str_list(key: str) -> list[str]:
        val = data.get(key)
        if not isinstance(val, list):
            return []
        return [str(x).strip() for x in val if str(x).strip()][:8]

    return AiInsight(
        ok=True,
        provider=provider,
        risk_score=score,
        risk_level=level,
        summary=str(data.get("summary") or "").strip(),
        scam_types=_str_list("scam_types"),
        red_flags=_str_list("red_flags"),
        advice=_str_list("advice"),
        confidence=str(data.get("confidence") or "").strip() or None,
        model=model,
    )
