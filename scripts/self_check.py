"""本地自检：改完代码后跑一遍，避免明显回归。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FAILURES: list[str] = []


def ok(name: str) -> None:
    print(f"  OK  {name}")


def fail(name: str, detail: str) -> None:
    FAILURES.append(f"{name}: {detail}")
    print(f"  FAIL {name}: {detail}")


def check_imports() -> None:
    print("[imports]")
    try:
        import float_app  # noqa: F401
        ok("float_app import")
    except Exception as e:
        fail("float_app import", str(e))
    try:
        import app.analyze_service  # noqa: F401
        import app.strict_policy  # noqa: F401
        ok("analyze + strict_policy")
    except Exception as e:
        fail("core modules", str(e))
    try:
        import app.main  # noqa: F401
        ok("app.main (web)")
    except ImportError as e:
        ok(f"app.main skipped ({e})")
    except Exception as e:
        fail("app.main", str(e))


def check_company_extraction() -> None:
    print("[company]")
    from app.company import (
        best_company_name,
        extract_company_names,
        is_plausible_company_name,
    )

    scam_jd = (
        "职位描述微信扫码分享举报早九晚六带薪休假办公室福利待遇好岗位职责："
        "在抖音微信复制粘贴咱们的文案发送即可工作轻松简单好上手小白也能干，"
        "没有绩效考核。办公环境干净整洁公司"
    )
    names = extract_company_names(scam_jd)
    if names:
        fail("scam jd no false company", repr(names))
    else:
        ok("scam jd no false company")

    if is_plausible_company_name("办公环境干净整洁公司"):
        fail("reject descriptive fake company", "should be False")
    else:
        ok("reject descriptive fake company")

    good = extract_company_names("郑州军昶科技有限公司招聘客服，五险一金")
    if not good or good[0] != "郑州军昶科技有限公司":
        fail("real company name", repr(good))
    else:
        ok("real company name")

    boss = (
        "高先生 活跃\n"
        "郑州创颐商贸有限公司\n"
        "人事专员\n"
        "职位描述在抖音微信复制粘贴"
    )
    b = best_company_name(boss)
    if b != "郑州创颐商贸有限公司":
        fail("boss line company", repr(b))
    else:
        ok("boss line company")

    labeled = best_company_name("公司名称：深圳华兴劳务有限公司\n岗位：客服")
    if labeled != "深圳华兴劳务有限公司":
        fail("labeled company", repr(labeled))
    else:
        ok("labeled company")

    dot = best_company_name("高先生 · 郑州创颐商贸有限公司 · 招聘HR")
    if dot != "郑州创颐商贸有限公司":
        fail("dot segment company", repr(dot))
    else:
        ok("dot segment company")

    from app.analyze_service import analyze_full
    from app.biz_risk import analyze_biz_risk

    chuangyi = (
        "公司介绍我们是一家大型私域电商公司，主营白酒\n"
        "公司名称：郑州创颐商贸有限公司\n"
        "法定代表人：张素敏\n"
        "成立日期：2025-06-20\n"
        "企业类型：有限责任公司（自然人独资）\n"
        "注册资金：10万元\n"
        "岗位职责：在抖音微信复制粘贴咱们的文案发送即可"
    )
    biz = analyze_biz_risk(chuangyi)
    if not biz.warnings or biz.score_bonus < 10:
        fail("chuangyi biz signals", repr(biz.to_dict()))
    else:
        ok("chuangyi biz signals")

    r = analyze_full(chuangyi, "auto", use_ai=False, provider="none", save_history=False)
    if r.get("risk_level") == "低危" and not r.get("biz_warnings"):
        fail("chuangyi not low only", r.get("risk_level"))
    elif r.get("risk_level_display") == "较安全":
        fail("old label 较安全", r.get("risk_level_display"))
    else:
        ok(f"chuangyi combined -> {r.get('risk_level_display')} ({r.get('risk_score')}分)")

    from app.biz_summary import parse_biz_summary
    from app.engine import reload_patterns

    tyc = "天眼查\n测试公司\n参保人数：0人\n实缴资本：0万元"
    s = parse_biz_summary(tyc)
    if s.score_bonus < 10:
        fail("tyc paste parse", repr(s.to_dict()))
    else:
        ok("tyc paste parse")

    ri = reload_patterns()
    if not ri.get("ok"):
        fail("reload patterns", str(ri))
    else:
        ok(f"reload patterns v{ri.get('version')}")


def check_analyze_pipeline() -> None:
    print("[analyze]")
    from app.analyze_service import analyze_full

    sample = "日结300 加微信 17-22岁 打字文员 先交培训费"
    r = analyze_full(sample, "auto", use_ai=False, provider="none", save_history=False)
    for key in ("risk_score", "risk_level", "headline", "actions", "content_type_label"):
        if key not in r:
            fail("analyze result keys", f"missing {key}")
            return
    if not r.get("headline"):
        fail("analyze headline", "empty")
    elif len(r.get("actions") or []) < 1:
        fail("analyze actions", "empty")
    else:
        ok("analyze pipeline")


def check_content_detect() -> None:
    print("[content_type]")
    from app.content_detect import resolve_content_type

    ct, label = resolve_content_type("岗位职责：复制粘贴 加微信详聊")
    if ct not in ("job", "chat", "general"):
        fail("content type", ct)
    else:
        ok(f"auto type -> {ct} ({label})")


def check_settings() -> None:
    print("[settings]")
    from app.settings import get_settings, get_ocr_engine_pref

    s = get_settings()
    if "ocr_engine" not in s:
        fail("settings defaults", "missing ocr_engine")
    else:
        ok("settings load")
    pref = get_ocr_engine_pref()
    if pref not in ("fast", "auto", "paddle", "rapid", "windows"):
        fail("ocr pref", pref)
    else:
        ok(f"ocr pref -> {pref}")


def check_float_guard_build() -> None:
    print("[float_ui]")
    try:
        import tkinter as tk
        from float_app import FloatGuard

        root = tk.Tk()
        root.withdraw()
        app = FloatGuard()
        required = (
            "input_box",
            "company_input",
            "score_band",
            "headline_label",
            "result_box",
            "type_badge",
            "co_card",
            "ai_row",
        )
        missing = [a for a in required if not hasattr(app, a)]
        if missing:
            fail("FloatGuard widgets", ", ".join(missing))
        else:
            ok("FloatGuard builds")
        try:
            app._card(app.panel, pady=(0, 6))
            ok("_card pady override")
        except TypeError as e:
            fail("_card pady override", str(e))
        app.root.update_idletasks()
        app._show_panel()
        app.root.update_idletasks()
        ph = app.panel.winfo_height()
        if ph < 100:
            ok("bottom dock (panel not sized in headless)")
        else:
            for name, w in (("co_card", app.co_card), ("ai_row", app.ai_row)):
                y = w.winfo_rooty() - app.panel.winfo_rooty()
                h = w.winfo_height()
                if h < 8 or y + h > ph + 2:
                    fail(f"{name} visible", f"y={y} h={h} panel_h={ph}")
                else:
                    ok(f"{name} in viewport")
        app.root.destroy()
        root.destroy()
    except Exception as e:
        fail("FloatGuard build", str(e))


def check_api_app() -> None:
    print("[api]")
    try:
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        h = client.get("/api/health")
        if h.status_code != 200:
            fail("/api/health", str(h.status_code))
        else:
            ok("/api/health")
        r = client.post(
            "/api/analyze",
            json={"text": "加微信日结300", "content_type": "auto", "use_ai": False},
        )
        if r.status_code != 200:
            fail("/api/analyze", str(r.status_code))
        elif "headline" not in r.json():
            fail("/api/analyze body", "missing headline")
        else:
            ok("/api/analyze")
    except ImportError:
        ok("/api skipped (no TestClient)")
    except Exception as e:
        fail("api", str(e))


def main() -> int:
    print("=== job-scam-guard self_check ===\n")
    check_imports()
    check_company_extraction()
    check_content_detect()
    check_analyze_pipeline()
    check_settings()
    check_float_guard_build()
    check_api_app()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
