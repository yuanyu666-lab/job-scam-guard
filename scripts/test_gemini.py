"""Gemini 连通性测试。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai_insight import insight_to_dict
from app.engine import analyze_text
from app.gemini import analyze_with_gemini, is_configured, load_config


def main() -> int:
    if not is_configured():
        print("失败：未配置 Gemini（data/gemini_config.json）")
        return 1

    cfg = load_config()
    print(f"模型: {cfg.get('model')}")
    print("正在请求 Gemini…")

    sample = "日结300 加微信 17-22岁 打字文员 小白"
    rule = analyze_text(sample, "chat")
    data = insight_to_dict(analyze_with_gemini(sample, "chat", rule))

    print(json.dumps(data, ensure_ascii=False, indent=2))
    if data.get("ok"):
        print("\n【成功】ok = true")
        return 0
    print(f"\n【失败】{data.get('error')}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
