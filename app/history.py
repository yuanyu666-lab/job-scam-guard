"""本地检测历史（jsonl）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.settings import get_settings

HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "history.jsonl"


def _ensure_dir() -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)


def append_history(text: str, result: dict, content_type: str) -> None:
    _ensure_dir()
    max_n = int(get_settings().get("history_max") or 10)
    company = None
    try:
        from app.company import best_company_name

        company = best_company_name(text)
    except Exception:
        pass
    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "content_type": content_type,
        "preview": text[:120],
        "text": text[:500],
        "company": company,
        "risk_score": result.get("risk_score"),
        "risk_level": result.get("risk_level"),
        "risk_level_display": result.get("risk_level_display"),
        "headline": result.get("headline"),
    }
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    _trim(max_n)


def _trim(max_n: int) -> None:
    if not HISTORY_PATH.exists() or max_n < 1:
        return
    lines = [
        ln for ln in HISTORY_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    if len(lines) <= max_n:
        return
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines[-max_n:]) + "\n")


def _read_all() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    out: list[dict] = []
    for ln in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


def list_history(limit: int = 10) -> list[dict]:
    items = _read_all()
    return list(reversed(items[-limit:]))


def search_history(query: str, limit: int = 20) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return list_history(limit)
    items = _read_all()
    matched = []
    for it in reversed(items):
        blob = " ".join(
            str(it.get(k, ""))
            for k in ("preview", "text", "company", "headline", "risk_level")
        ).lower()
        if q in blob:
            matched.append(it)
        if len(matched) >= limit:
            break
    return matched


def export_history_markdown(limit: int = 20) -> str:
    items = list_history(limit)
    lines = ["# 招聘防骗 · 检测历史", ""]
    for it in items:
        at = (it.get("at") or "")[:19].replace("T", " ")
        lvl = it.get("risk_level_display") or it.get("risk_level") or "?"
        sc = it.get("risk_score", "—")
        co = it.get("company") or "—"
        lines.append(f"## {at} · {lvl} ({sc}分) · {co}")
        if it.get("headline"):
            lines.append(f"> {it['headline']}")
        lines.append("")
        lines.append("```")
        lines.append((it.get("text") or it.get("preview") or "")[:400])
        lines.append("```")
        lines.append("")
    return "\n".join(lines)
