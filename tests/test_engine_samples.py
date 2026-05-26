"""规则引擎样例测试（无需 fastapi）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.analyze_service import analyze_full
from app.biz_summary import parse_biz_summary
from app.engine import init_patterns, reload_patterns


def test_reload_patterns():
    info = reload_patterns()
    assert info.get("ok") is True
    assert info.get("categories", 0) > 5


def test_scam_sample_high_risk():
    init_patterns()
    text = "日结300 加微信 17-22岁 打字文员 先交培训费"
    r = analyze_full(text, "auto", use_ai=False, provider="none", save_history=False)
    assert r["risk_score"] >= 40
    assert r["risk_level"] in ("中危", "高危")


def test_biz_summary_social_zero():
    tyc = "天眼查\n郑州某某有限公司\n参保人数：0人\n实缴资本：0万元\n经营异常"
    s = parse_biz_summary(tyc)
    assert s.score_bonus >= 20
    assert any("参保" in w for w in s.warnings)


def test_chuangyi_sample():
    text = (
        "公司名称：郑州创颐商贸有限公司\n"
        "成立日期：2025-06-20\n"
        "注册资金：10万元\n"
        "企业类型：有限责任公司（自然人独资）\n"
        "岗位职责：在抖音微信复制粘贴咱们的文案发送即可"
    )
    r = analyze_full(text, "auto", use_ai=False, provider="none", save_history=False)
    assert r["risk_level"] == "高危"
    assert r.get("score_breakdown")


if __name__ == "__main__":
    test_reload_patterns()
    test_scam_sample_high_risk()
    test_biz_summary_social_zero()
    test_chuangyi_sample()
    print("tests OK")
