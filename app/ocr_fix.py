"""OCR 常见错字纠正（招聘/公司名场景）。"""

from __future__ import annotations

import re

from app.settings import get_settings

# 错字 -> 正字（按长度降序避免短词误替换）
_CHAR_FIXES: list[tuple[str, str]] = [
    ("有限公同", "有限公司"),
    ("科技公同", "科技公司"),
    ("责仼", "责任"),
    ("注冊", "注册"),
    ("资木", "资本"),
    ("法走代表", "法定代表"),
    ("参保人教", "参保人数"),
    ("实缴资木", "实缴资本"),
    ("经菅", "经营"),
    ("异带", "异常"),
    ("微倍", "微信"),
    ("抖育", "抖音"),
    ("复剌", "复制"),
    ("粘貼", "粘贴"),
    ("招骋", "招聘"),
    ("面式", "面试"),
    ("薪資", "薪资"),
]

_COMPANY_SPACING = re.compile(
    r"([\u4e00-\u9fff])\s+([\u4e00-\u9fff])"
)


def fix_ocr_text(text: str) -> str:
    if not get_settings().get("ocr_post_fix", True):
        return text
    out = text
    for wrong, right in _CHAR_FIXES:
        out = out.replace(wrong, right)
    # 公司名行内多余空格（保留换行）
    lines = []
    for line in out.splitlines():
        if "公司" in line or "有限公司" in line:
            line = _COMPANY_SPACING.sub(r"\1\2", line)
        lines.append(line)
    return "\n".join(lines)
