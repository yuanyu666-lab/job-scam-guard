"""招聘防骗风险检测引擎（个人自用版）。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from app.strict_policy import (
    combo_bonus_adjustment,
    is_strict,
    recruitment_keywords_present,
    risk_level_from_score,
    risk_thresholds,
    score_compute_multiplier,
    weight_adjustment,
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "patterns.json"

_config: dict | None = None
_compiled: list[tuple[dict, list[re.Pattern[str]]]] = []


@dataclass
class MatchDetail:
    category_id: str
    category_name: str
    weight: int
    hits: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    risk_score: int
    risk_level: str
    matches: list[MatchDetail]
    suggestions: list[str]
    highlight_terms: list[str] = field(default_factory=list)
    urls_found: list[str] = field(default_factory=list)
    url_warnings: list[str] = field(default_factory=list)


def _risk_level(score: int) -> str:
    return risk_level_from_score(score)


def _compute_score(
    weights: list[int], url_count: int, match_ids: set[str], config: dict
) -> int:
    if not weights and url_count == 0:
        return 0
    if not weights:
        score = min(100, 30 + url_count * 8)
    else:
        ordered = sorted(weights, reverse=True)
        base = ordered[0] + sum(ordered[1:]) * 0.35
        url_bonus = min(18, url_count * 9)
        score = min(100, int(round(base + url_bonus)))

    for rule in config.get("combo_rules", []):
        need = set(rule.get("ids", []))
        if need and need.issubset(match_ids):
            score = min(
                100,
                score + combo_bonus_adjustment(int(rule.get("bonus", 0))),
            )
    mul = score_compute_multiplier()
    if mul != 1.0:
        score = min(100, int(round(score * mul)))
    return score


def _default_suggestions(
    score: int, matches: list[MatchDetail], config: dict | None = None
) -> list[str]:
    mid, _ = risk_thresholds()
    if score < mid:
        if is_strict():
            return [
                "严格模式：未发现典型诈骗话术，仍默认建议核实企业工商、参保与合同主体。",
                "勿先转账、交押金、出借银行卡/手机卡；勿下载不明工作 App。",
                "面试前书面确认：底薪、社保缴纳月、合同甲方与办公地址。",
            ]
        return [
            "未发现典型诈骗话术，仍建议核实企业工商、参保与合同主体。",
            "勿先转账、交押金、出借银行卡/手机卡。",
        ]
    base = [
        "在 BOSS/智联等平台内沟通留痕，勿轻易加私人微信或进陌生群。",
        "凡要求先交钱、下载不明 App、垫付刷单的一律拒绝。",
    ]
    if score >= 70:
        base.insert(0, "建议停止沟通，保留截图，勿转账、勿出借账户。")

    cat_ids = {m.category_id for m in matches}
    tips_map = {
        "transfer": "「居家高薪」「面试考核刷单」= 求职变刷单，公安部明确刷单即诈骗。",
        "zhaozhuanpei": "招转培/培训贷：先贬低能力再卖课，勿签培训协议、勿办培训贷。",
        "tool_person": "两部手机/代理客服=帮信「手机口」，可能承担刑事责任。",
        "fee": "入职前不收培训费、押金、工牌费、内推费。",
        "paid_referral": "付费内推、包进大厂多为骗局，正规校招不收费。",
        "fake_offer": "天降 offer 且非投递公司发出 → 高度可疑，勿点测评链接。",
        "phishing": "勿下载来路不明工作端 App，勿屏幕共享、勿点陌生链接。",
        "off_platform": "急于脱离平台是为规避封号与追溯。",
        "impersonation": "零门槛+超高薪需警惕，对照官网薪资与岗位要求。",
        "privacy": "勿出借身份证、银行卡、手机卡给他人办业务。",
        "pyramid": "拉人头、入门费属于传销特征。",
        "resume_fraud": "只收简历、代发职位可能涉及简历倒卖或帮信。",
        "typing_lure": "「简单打字+小白可做」多为引流，后续常刷单、收费或招转培。",
        "target_youth": "限定 17-22 岁、零零后话术，专盯学生/应届生。",
        "vague_jd": "只写冬暖夏凉、团建氛围，不写薪资与岗位职责 → 高度可疑。",
    }
    for cid in cat_ids:
        if cid in tips_map:
            base.append(tips_map[cid])

    if config:
        for rule in config.get("combo_rules", []):
            need = set(rule.get("ids", []))
            if need and need.issubset(cat_ids) and rule.get("tip"):
                base.append(str(rule["tip"]))

    seen: set[str] = set()
    out: list[str] = []
    for t in base:
        if t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= 6:
            break
    return out


def _collect_highlight_terms(matches: list[MatchDetail]) -> list[str]:
    terms: list[str] = []
    for m in matches:
        for hit in m.hits:
            if hit.startswith("关键词: "):
                terms.append(hit[5:])
    return list(dict.fromkeys(terms))


def init_patterns() -> None:
    """加载规则；改 patterns.json 后可 reload_patterns() 无需重启。"""
    global _config, _compiled
    with open(DATA_PATH, encoding="utf-8") as f:
        _config = json.load(f)
    _compiled = []
    categories = list(_config.get("categories", []))
    categories.extend(_active_platform_packs(_config))
    for cat in categories:
        patterns = [re.compile(p, re.IGNORECASE) for p in cat.get("patterns", [])]
        _compiled.append((cat, patterns))


def reload_patterns() -> dict:
    """热重载 patterns.json，返回版本信息。"""
    init_patterns()
    cfg = get_config()
    return {
        "ok": True,
        "version": cfg.get("version"),
        "categories": len(cfg.get("categories", [])),
        "packs": _active_platform_packs(cfg, count_only=True),
    }


def _active_platform_packs(config: dict, count_only: bool = False) -> list:
    try:
        from app.settings import get_settings

        enabled_list = get_settings().get("enabled_platform_packs")
    except ImportError:
        enabled_list = ["boss", "zhilian", "wechat"]
    enabled_set = set(enabled_list) if enabled_list is not None else None

    out: list = []
    for pack in config.get("platform_packs", []):
        pid = str(pack.get("id", "")).strip()
        if not pid:
            continue
        if enabled_set is not None:
            if pid not in enabled_set:
                continue
        elif not pack.get("enabled_by_default", True):
            continue
        if count_only:
            out.append(pid)
            continue
        out.append(
            {
                "id": f"pack_{pid}",
                "name": pack.get("name", pid),
                "weight": int(pack.get("weight", 8)),
                "keywords": list(pack.get("keywords", [])),
                "patterns": list(pack.get("patterns", [])),
                "meta": pack.get("meta"),
            }
        )
    return out


def get_config() -> dict:
    if _config is None:
        init_patterns()
    return _config  # type: ignore[return-value]


def extract_urls(text: str) -> list[str]:
    pattern = r"https?://[^\s<>\"']+|[a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com|cn|net|org|io|cc|top|xyz|vip)(?:/[^\s]*)?"
    return list(dict.fromkeys(re.findall(pattern, text, re.IGNORECASE)))


def check_url(url: str, config: dict) -> str | None:
    raw = url if "://" in url else f"http://{url}"
    try:
        host = urlparse(raw).netloc.lower()
    except Exception:
        return "无法解析的链接"
    if not host:
        return "无法解析的链接"

    for token in config.get("suspicious_domains", []):
        if token.lower() in host:
            return f"域名含可疑仿冒特征「{token}」"

    for bad in config.get("phishing_domains", []):
        if bad.lower() in host or host.endswith("." + bad.lower()):
            return f"已知招聘钓鱼域名特征「{bad}」"

    if host.count("-") >= 2 and any(k in host for k in ("job", "career", "hire", "hr", "recruit")):
        return "招聘类域名结构异常，疑似仿冒"

    trusted = config.get("trusted_email_domains", [])
    if not any(host.endswith(t) or host == t for t in trusted):
        if re.search(r"(job|career|hire|hr|recruit|zhipin|boss)", host):
            return "非知名域名含招聘字样，请人工核验"

    return None


def _apply_heuristics(
    text: str,
    matches: list[MatchDetail],
    match_ids: set[str],
    config: dict,
) -> list[MatchDetail]:
    """补充规则：福利堆砌却无薪资、典型文员骗局组合。"""
    extra: list[MatchDetail] = []
    existing_ids = set(match_ids)

    for rule in config.get("heuristic_rules", []):
        perks = rule.get("perk_keywords", [])
        duties = rule.get("duty_keywords", [])
        min_perks = int(rule.get("min_perks", 2))
        perk_hit = sum(1 for k in perks if k in text)
        duty_hit = any(k in text for k in duties)
        if perk_hit >= min_perks and not duty_hit:
            rid = str(rule.get("id", "no_salary_many_perks"))
            if rid not in existing_ids:
                extra.append(
                    MatchDetail(
                        category_id=rid,
                        category_name=str(rule.get("desc", "综合风险")),
                        weight=22,
                        hits=[f"福利话术 {perk_hit} 处，未见薪资/岗位职责"],
                    )
                )
                match_ids.add(rid)
                existing_ids.add(rid)

    young = bool(
        re.search(r"1[7-9]\s*[-~到至]\s*2[0-5]", text)
        or "17-22" in text.replace(" ", "")
    )
    typing = "打字" in text and any(k in text for k in ("小白", "无经验", "没经验", "要求不高"))

    if young and typing and "typing_lure" not in existing_ids:
        extra.append(
            MatchDetail(
                category_id="typing_lure",
                category_name="打字/文员诱饵",
                weight=30,
                hits=["组合: 低龄 + 打字零门槛"],
            )
        )
        match_ids.add("typing_lure")
        existing_ids.add("typing_lure")

    if young and "target_youth" not in existing_ids:
        extra.append(
            MatchDetail(
                category_id="target_youth",
                category_name="收割年轻人",
                weight=26,
                hits=["组合: 限定低龄/应届生"],
            )
        )
        match_ids.add("target_youth")

    return extra


def _normalize_text(text: str) -> str:
    """统一空白与常见干扰字符，提升命中率。"""
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = re.sub(r"[\t\r]+", "\n", text)
    return text


def analyze_text(text: str, content_type: str = "general") -> AnalysisResult:
    config = get_config()
    text = _normalize_text(text)
    text_lower = text.lower()
    matches: list[MatchDetail] = []
    weights: list[int] = []
    match_ids: set[str] = set()

    for cat, patterns in _compiled:
        hits: list[str] = []
        for kw in cat["keywords"]:
            if kw.lower() in text_lower:
                hits.append(f"关键词: {kw}")
        for pat in patterns:
            for m in pat.findall(text)[:3]:
                snippet = m if isinstance(m, str) else m[0]
                hits.append(f"模式: {snippet[:40]}")

        if hits:
            w = weight_adjustment(cat["weight"])
            cid = cat["id"]
            if content_type == "chat" and cid == "off_platform":
                w = min(w + 5, 38)
            if content_type == "job" and cid in (
                "impersonation",
                "zhaozhuanpei",
                "typing_lure",
                "target_youth",
                "vague_jd",
                "private_ecommerce",
            ):
                w = min(w + 4, 40)
            match_ids.add(cid)
            weights.append(w)
            matches.append(
                MatchDetail(
                    category_id=cat["id"],
                    category_name=cat["name"],
                    weight=w,
                    hits=hits[:6],
                )
            )

    urls = extract_urls(text)
    url_warnings: list[str] = []
    for u in urls:
        warn = check_url(u, config)
        if warn:
            url_warnings.append(f"{u} — {warn}")

    extra_matches = _apply_heuristics(text, matches, match_ids, config)
    if extra_matches:
        matches.extend(extra_matches)
        weights.extend(m.weight for m in extra_matches)

    score = _compute_score(weights, len(url_warnings), match_ids, config)
    if {"typing_lure", "target_youth"}.issubset(match_ids) and len(match_ids) >= 2:
        score = max(score, 75)
    if {"typing_lure", "target_youth", "vague_jd"}.issubset(match_ids):
        score = max(score, 85)

    return AnalysisResult(
        risk_score=score,
        risk_level=_risk_level(score),
        matches=matches,
        suggestions=_default_suggestions(score, matches, config),
        highlight_terms=_collect_highlight_terms(matches),
        urls_found=urls,
        url_warnings=url_warnings,
    )


def result_to_dict(result: AnalysisResult) -> dict:
    return {
        "risk_score": result.risk_score,
        "risk_level": result.risk_level,
        "matches": [
            {
                "category_id": m.category_id,
                "category_name": m.category_name,
                "weight": m.weight,
                "hits": m.hits,
            }
            for m in result.matches
        ],
        "suggestions": result.suggestions,
        "highlight_terms": result.highlight_terms,
        "urls_found": result.urls_found,
        "url_warnings": result.url_warnings,
    }
