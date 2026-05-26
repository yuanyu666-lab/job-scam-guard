"""统一分析入口：本地规则 + 工商信号 + 可选 Gemini / DeepSeek。"""



from __future__ import annotations



from app.ai_insight import AiInsight

from app.ai_merge import merge_rule_and_ai

from app.ai_router import (

    analyze_with_cloud,

    resolve_provider,

    should_call_ai_for_rule,

)

from app.biz_risk import analyze_biz_risk, apply_biz_risk

from app.content_detect import resolve_content_type

from app.engine import analyze_text

from app.history import append_history

from app.ocr_fix import fix_ocr_text

from app.score_explain import build_score_breakdown, format_breakdown_text

from app.settings import get_settings

from app.strict_policy import apply_strict_score_floor, is_strict, risk_level_from_score

from app.summary import enrich_result





def analyze_full(

    text: str,

    content_type: str = "auto",

    *,

    use_ai: bool | None = None,

    provider: str | None = None,

    save_history: bool | None = None,

    apply_ocr_fix: bool = True,

) -> dict:

    stripped = text.strip()

    if apply_ocr_fix:

        stripped = fix_ocr_text(stripped)

    ct, label = resolve_content_type(stripped, content_type)

    rule = analyze_text(stripped, ct)

    biz = analyze_biz_risk(stripped)

    rule = apply_biz_risk(rule, biz)



    ai: AiInsight | None = None

    p = resolve_provider(provider)

    call_ai, skip_reason = should_call_ai_for_rule(

        rule, use_ai=use_ai, provider=provider, biz_score_bonus=biz.score_bonus

    )

    if call_ai:

        ai = analyze_with_cloud(stripped, ct, rule, provider=provider)

    elif skip_reason and use_ai is not False:

        ai = AiInsight(

            ok=False,

            skipped=True,

            skip_reason=skip_reason,

            provider=p,

        )



    result = merge_rule_and_ai(rule, ai)

    result["biz_risk"] = biz.to_dict()

    result["biz_warnings"] = biz.warnings



    raw_score = int(result.get("risk_score") or 0)

    floor_note = 0

    if is_strict():

        before = raw_score

        new_score = apply_strict_score_floor(

            stripped, raw_score, len(result.get("matches") or [])

        )

        if new_score > before:

            floor_note = new_score - before

        result["risk_score"] = new_score

        result["risk_level"] = risk_level_from_score(new_score)



    breakdown = build_score_breakdown(

        rule, biz_bonus=biz.score_bonus, strict_floor_applied=floor_note

    )

    result["score_breakdown"] = breakdown

    result["score_breakdown_text"] = format_breakdown_text(

        breakdown, int(result["risk_score"]), result["risk_level"]

    )

    result["ai_decision"] = (

        "called"

        if call_ai

        else ("skipped: " + skip_reason if skip_reason else "off")

    )



    result = enrich_result(

        result, content_type=ct, content_label=label, biz_warnings=biz.warnings

    )



    do_save = (

        save_history

        if save_history is not None

        else bool(get_settings().get("save_history", True))

    )

    if do_save and stripped:

        append_history(stripped, result, ct)

    return result

