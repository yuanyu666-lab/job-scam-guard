"""DeepSeek 连通性测试（供 测试DeepSeek.bat 调用）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai_insight import insight_to_dict
from app.deepseek import analyze_with_deepseek, is_configured, load_config
from app.engine import analyze_text


def main() -> int:
    if not is_configured():
        print("失败：未配置 DeepSeek")
        print("  1. 复制 data/deepseek_config.json.example")
        print("  2. 改名为 data/deepseek_config.json")
        print("  3. 填入 api_key（https://platform.deepseek.com/api_keys）")
        return 1

    cfg = load_config()
    print(f"模型: {cfg.get('model', 'deepseek-chat')}")
    print("正在请求 DeepSeek（约 3～10 秒）…")

    sample = "日结300 加微信 17-22岁 打字文员 小白"
    rule = analyze_text(sample, "chat")
    insight = analyze_with_deepseek(sample, "chat", rule)
    data = insight_to_dict(insight)

    print()
    print("---------- 返回结果 ----------")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("------------------------------")
    print()

    if data.get("ok"):
        print("【成功】ok = true  ← 看到这个就说明接通了")
        print(f"  模型: {data.get('model')}")
        print(f"  评分: {data.get('risk_score')} ({data.get('risk_level')})")
        if data.get("summary"):
            print(f"  摘要: {data.get('summary')}")
        return 0

    print("【失败】ok = false")
    print(f"  原因: {data.get('error') or '未知'}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
