"""根据文本自动判断内容类型（职位 / 聊天 / 通用）。"""

from __future__ import annotations

import re

CHAT_SIGNALS = (
    "微信",
    "加微",
    "vx",
    "v信",
    "私聊",
    "boss",
    "hr",
    "您好",
    "亲",
    "在吗",
    "聊一下",
    "加我",
    "whatsapp",
    "telegram",
    "tg",
    "日结",
    "先加",
    "详聊",
)

JOB_SIGNALS = (
    "岗位职责",
    "任职要求",
    "职位描述",
    "工作地点",
    "薪资",
    "福利",
    "五险一金",
    "双休",
    "学历要求",
    "工作经验",
    "jd",
    "招聘",
    "岗位",
    "月薪",
    "年薪",
    "入职",
    "简历",
)

TYPE_LABELS = {"job": "职位描述", "chat": "聊天记录", "general": "通用文本"}


def detect_content_type(text: str) -> str:
    t = text.strip()
    if not t:
        return "general"
    lower = t.lower()

    chat_score = 0
    for s in CHAT_SIGNALS:
        if s.lower() in lower:
            chat_score += 1

    job_score = 0
    for s in JOB_SIGNALS:
        if s.lower() in lower or s in t:
            job_score += 1

    # 短消息、多行对话更像聊天
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if len(lines) >= 4 and len(t) < 800:
        chat_score += 1
    if re.search(r"[:：]\s*\S", t) and len(lines) >= 2:
        chat_score += 1
    if len(t) > 400 and job_score >= 1:
        job_score += 1

    if chat_score >= 2 and chat_score > job_score:
        return "chat"
    if job_score >= 2 and job_score >= chat_score:
        return "job"
    if chat_score >= 3:
        return "chat"
    if job_score >= 1 and len(t) > 200:
        return "job"
    return "general"


def resolve_content_type(text: str, explicit: str | None = None) -> tuple[str, str]:
    """返回 (类型 key, 中文标签)。"""
    from app.settings import get_settings

    auto = get_settings().get("auto_content_type", True)
    exp = (explicit or "auto").strip().lower()
    if not auto and exp in ("job", "chat", "general"):
        return exp, TYPE_LABELS[exp]
    detected = detect_content_type(text)
    return detected, TYPE_LABELS.get(detected, "通用文本")
