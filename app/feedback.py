"""误报/漏报反馈（本地 jsonl）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

FEEDBACK_PATH = Path(__file__).resolve().parent.parent / "data" / "feedback.jsonl"


def append_feedback(
    text: str,
    result: dict,
    *,
    label: str = "false_positive",
    comment: str = "",
) -> dict:
    """label: false_positive | false_negative | other"""
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "comment": comment.strip()[:500],
        "risk_score": result.get("risk_score"),
        "risk_level": result.get("risk_level"),
        "preview": text[:200],
        "text": text[:800],
        "headline": result.get("headline"),
        "match_ids": [
            m.get("category_id")
            for m in (result.get("matches") or [])
            if m.get("category_id")
        ],
    }
    with open(FEEDBACK_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry
