"""企业核查：默认免费（打开公示系统），可选天眼查 API（付费）。"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "company_api.json"
TIANYANCHA_BASEINFO = "http://open.api.tianyancha.com/services/open/ic/baseinfo/normal"

_FORMAL_SUFFIXES = (
    "股份有限公司",
    "有限责任公司",
    "集团有限公司",
    "科技有限公司",
    "有限公司",
)
_COMPANY_SUFFIX = "|".join(re.escape(s) for s in _FORMAL_SUFFIXES)
COMPANY_NAME_RE = re.compile(
    rf"([\u4e00-\u9fffA-Za-z0-9（）()·]{{2,40}}?(?:{_COMPANY_SUFFIX}))"
)
_BAD_NAME_PARTS = (
    "办公环境",
    "干净整洁",
    "福利待遇",
    "岗位职责",
    "职位描述",
    "工作内容",
    "工作轻松",
    "带薪休假",
    "早九晚",
    "复制粘贴",
    "扫码分享",
    "绩效考核",
    "好上手",
    "小白也能",
    "是一家",
    "招聘",
    "我们",
    "贵司",
    "面试",
    "岗位",
    "工作",
    "福利",
    "职责",
    "待遇",
    "环境",
    "干净",
    "整洁",
    "办公室",
    "分享举报",
    "微信",
    "抖音",
    "日结",
    "兼职",
    "居家",
    "轻松简单",
    "文案",
    "发送",
    "即可",
    "简单",
    "上手",
    "活跃",
    "先生",
    "女士",
    "复制",
    "粘贴",
    "详聊",
    "扫码",
    "举报",
)

from app.strict_policy import company_autofill_min_score

# 仅匹配较短商号 +「公司」——默认不参与泛匹配，仅标签/整行命中时使用
COMPANY_SHORT_CO_RE = re.compile(
    r"([\u4e00-\u9fff]{2,6}公司)"
)
COMPANY_SHORT_RE = re.compile(
    r"([\u4e00-\u9fff]{2,8}(?:科技|网络|信息|控股|集团)(?!公司))"
)

# 明确标注的公司名（高置信）
LABELED_RES = (
    re.compile(
        r"(?:公司|企业)(?:名称|全称)?[:：]\s*"
        rf"([\u4e00-\u9fffA-Za-z0-9（）()·]{{2,40}}{_COMPANY_SUFFIX})"
    ),
    re.compile(
        r"(?:招聘单位|用工单位|所属公司|雇主)[:：]\s*"
        rf"([\u4e00-\u9fffA-Za-z0-9（）()·]{{2,40}}{_COMPANY_SUFFIX})"
    ),
)

# BOSS / 智联等：「··· 郑州XX有限公司 · HR」
DOT_SEG_RE = re.compile(
    rf"[·•|｜]\s*([\u4e00-\u9fffA-Za-z0-9]{{2,24}}(?:{_COMPANY_SUFFIX}))\s*[·•|｜]"
)

# 行业/地域词：正规公司名主体通常含其中之一
_BUSINESS_TOKENS = (
    "商贸", "贸易", "科技", "网络", "信息", "软件", "数据", "智能", "技术",
    "实业", "控股", "集团", "投资", "管理", "咨询", "文化", "传媒", "广告",
    "劳务", "人力", "资源", "教育", "医疗", "生物", "环保", "能源", "材料",
    "建设", "工程", "装饰", "物业", "餐饮", "食品", "服装", "家具", "百货",
    "电子", "通信", "电力", "机械", "汽车", "物流", "供应链", "进出口",
    "金融", "保险", "证券", "基金", "银行", "租赁", "担保", "会计", "律",
    "酒店", "旅游", "农业", "化工", "印刷", "包装", "检测", "认证",
)

_CITY_PREFIXES = (
    "北京", "上海", "天津", "重庆", "广州", "深圳", "杭州", "南京", "苏州",
    "武汉", "成都", "西安", "郑州", "长沙", "合肥", "福州", "厦门", "济南",
    "青岛", "大连", "沈阳", "哈尔滨", "长春", "石家庄", "太原", "南昌",
    "昆明", "贵阳", "南宁", "海口", "兰州", "银川", "西宁", "乌鲁木齐",
    "呼和浩特", "无锡", "宁波", "温州", "东莞", "佛山", "珠海", "中山",
    "河南", "河北", "山东", "江苏", "浙江", "广东", "四川", "湖北", "湖南",
    "安徽", "福建", "陕西", "辽宁", "吉林", "黑龙江",
)

# 招聘话术/描述性短语，不是公司名（见 _BAD_NAME_PARTS）

FREE_CHECKLIST = [
    "经营状态是否为「存续 / 在业」",
    "注册资本多少？实缴资本是否为空、0 或未公示",
    "最新年报 → 社保信息 → 城镇职工基本养老保险「参保人数」",
    "参保人数是否明显偏少（如 0～2 人却大量招聘）",
    "成立时间是否过新且招聘规模异常",
]


@dataclass
class CompanyProfile:
    name: str
    reg_status: str | None = None
    reg_capital: str | None = None
    actual_capital: str | None = None
    social_staff_num: int | None = None
    staff_num_range: str | None = None
    legal_person: str | None = None
    credit_code: str | None = None
    reg_location: str | None = None
    estiblish_time: str | None = None
    flags: list[str] = field(default_factory=list)
    risk_level: str = "未知"
    source: str = "free_manual"
    check_guide: list[str] = field(default_factory=list)
    manual_links: dict[str, str] = field(default_factory=dict)
    raw_error: str | None = None


def load_api_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def is_configured() -> bool:
    cfg = load_api_config()
    token = (cfg.get("token") or "").strip()
    use_paid = cfg.get("use_paid_api", False)
    return bool(use_paid and token and token != "在此填写天眼查开放平台 Token")


def normalize_company_name(name: str) -> str:
    """去掉 OCR 在汉字间插入的空格，避免天眼查搜成「郑 州 军 昶」。"""
    name = name.strip().replace("\u3000", "")
    # 中文与中文之间的空格、换行
    name = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", name)
    # 公司名主体：去掉全部空白（中文公司名不应含空格）
    if re.search(r"[\u4e00-\u9fff]", name):
        name = re.sub(r"\s+", "", name)
    return name


def collapse_cjk_spaces(text: str) -> str:
    """合并汉字之间的空格/制表符，保留换行（BOSS 等平台一行一家公司）。"""
    text = text.replace("\u3000", " ")
    return re.sub(r"(?<=[\u4e00-\u9fff])[ \t]+(?=[\u4e00-\u9fff])", "", text)


def _name_prefix(name: str) -> str:
    for suf in _FORMAL_SUFFIXES + ("公司", "集团"):
        if name.endswith(suf):
            return name[: -len(suf)]
    return name


def _has_business_core(prefix: str) -> bool:
    if any(t in prefix for t in _BUSINESS_TOKENS):
        return True
    if any(prefix.startswith(c) and len(prefix) > len(c) for c in _CITY_PREFIXES):
        return True
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9&·]{1,24}", prefix):
        return True
    return False


def is_plausible_company_name(name: str) -> bool:
    """过滤招聘话术、描述句误识别为公司名。"""
    n = normalize_company_name(name.strip())
    if len(n) < 4 or len(n) > 40:
        return False
    if any(s in n for s in _BAD_NAME_PARTS):
        return False
    if n.startswith(("是", "为", "该", "本", "在", "有", "无", "及", "与", "及")):
        return False
    prefix = _name_prefix(n)
    if any(p in prefix for p in ("先生", "女士", "活跃", "人事", "专员", "经理", "招聘")):
        return False
    has_formal = any(n.endswith(s) for s in _FORMAL_SUFFIXES)
    if has_formal:
        return 2 <= len(prefix) <= 30 and _has_business_core(prefix)
    if n.endswith("公司"):
        return 2 <= len(prefix) <= 6 and _has_business_core(prefix)
    if n.endswith(("科技", "网络", "信息", "控股", "集团")):
        return 2 <= len(prefix) <= 8 and _has_business_core(prefix)
    return False


def _score_company_name(name: str) -> int:
    score = 0
    if "股份有限公司" in name:
        score += 12
    elif "有限责任公司" in name:
        score += 11
    elif name.endswith("科技有限公司"):
        score += 12
    elif "有限公司" in name:
        score += 10
    elif name.endswith("公司"):
        score += 4
    elif name.endswith(("科技", "网络", "信息", "控股", "集团")):
        score += 3
    if re.search(r"[A-Za-z]", name):
        score += 1
    if len(_name_prefix(name)) <= 4:
        score += 1
    prefix = _name_prefix(name)
    if any(prefix.startswith(c) for c in _CITY_PREFIXES):
        score += 2
    return score


def _drop_subsumed_names(names: list[str]) -> list[str]:
    """去掉被更长名称包含的短候选（如保留「郑州军昶科技有限公司」）。"""
    out: list[str] = []
    for n in names:
        if any(n != m and n in m for m in names):
            continue
        out.append(n)
    return out


def _add_candidate(scored: dict[str, int], raw: str, bonus: int) -> None:
    n = normalize_company_name(raw.strip())
    if not is_plausible_company_name(n):
        return
    s = _score_company_name(n) + bonus
    if n not in scored or s > scored[n]:
        scored[n] = s


def _extract_labeled(text: str, scored: dict[str, int]) -> None:
    for pat in LABELED_RES:
        for m in pat.finditer(text):
            _add_candidate(scored, m.group(1), 25)


def _extract_dot_segments(text: str, scored: dict[str, int]) -> None:
    for m in DOT_SEG_RE.finditer(text):
        _add_candidate(scored, m.group(1), 18)
    # 行内「高先生 · 郑州创颐商贸有限公司 · 招聘HR」末尾无分隔符
    for m in re.finditer(
        rf"[·•|｜]\s*([\u4e00-\u9fffA-Za-z0-9]{{2,24}}(?:{_COMPANY_SUFFIX}))\s*(?:[·•|｜]|$)",
        text,
    ):
        _add_candidate(scored, m.group(1), 16)


def _extract_whole_lines(text: str, scored: dict[str, int]) -> None:
    for line in text.splitlines():
        line = line.strip(" ·•|｜\t")
        if not line or len(line) > 48:
            continue
        for m in COMPANY_NAME_RE.finditer(line):
            name = m.group(1)
            if len(line) <= len(name) + 6:
                _add_candidate(scored, name, 20)


def _extract_generic(text: str, scored: dict[str, int]) -> None:
    for raw in COMPANY_NAME_RE.findall(text):
        _add_candidate(scored, raw, 0)


def extract_company_candidates(text: str) -> list[tuple[str, int]]:
    """返回 (公司名, 置信分) 列表，分数越高越可信。"""
    text = collapse_cjk_spaces(text)
    scored: dict[str, int] = {}
    _extract_labeled(text, scored)
    _extract_dot_segments(text, scored)
    _extract_whole_lines(text, scored)
    _extract_generic(text, scored)
    ranked = sorted(scored.items(), key=lambda x: (-x[1], -len(x[0])))
    names = _drop_subsumed_names([n for n, _ in ranked])
    score_map = dict(ranked)
    return [(n, score_map[n]) for n in names if n in score_map]


def best_company_name(text: str) -> str | None:
    """自动填公司栏：仅当置信足够高时返回。"""
    cands = extract_company_candidates(text)
    if not cands:
        return None
    name, score = cands[0]
    return name if score >= company_autofill_min_score() else None


def extract_company_names(text: str, limit: int = 3) -> list[str]:
    return [n for n, s in extract_company_candidates(text) if s >= company_autofill_min_score()][
        :limit
    ]


def platform_urls(name: str) -> dict[str, str]:
    """各平台搜索页（免费网页人工查看）。"""
    clean = normalize_company_name(name)
    q = urllib.parse.quote(clean, safe="")
    return {
        "tianyancha": f"https://www.tianyancha.com/search?key={q}",
        "qcc": f"https://www.qcc.com/web/search?key={q}",
        "aiqicha": f"https://aiqicha.baidu.com/s?q={q}",
        "gsxt": "https://www.gsxt.gov.cn/index.html",
    }


def manual_search_links(name: str) -> dict[str, str]:
    u = platform_urls(name)
    return {
        "天眼查": u["tianyancha"],
        "企查查": u["qcc"],
        "爱企查": u["aiqicha"],
        "国家企业信用公示系统": u["gsxt"],
    }


def open_platform(name: str, platform: str) -> str:
    clean = normalize_company_name(name)
    if len(clean) < 4:
        raise ValueError("公司名过短，请检查 OCR 是否漏字或手动改为工商全称")
    urls = platform_urls(clean)
    if platform not in urls:
        raise ValueError(f"未知平台: {platform}")
    webbrowser.open(urls[platform])
    return urls[platform]


def open_free_in_browser(name: str, platform: str = "tianyancha") -> str:
    return open_platform(name, platform)


def query_company(name: str, *, paid: bool = False) -> CompanyProfile:
    name = name.strip()
    if not name:
        raise ValueError("请输入公司全称")
    if paid and is_configured():
        return _query_tianyancha(name)
    return _query_free_guide(name)


def _query_free_guide(name: str) -> CompanyProfile:
    links = manual_search_links(name)
    profile = CompanyProfile(
        name=name,
        source="free_manual",
        manual_links=links,
        check_guide=[
            "免费方式无法自动拉取数据，请按下面步骤在网页上核对：",
            "① 打开「国家企业信用信息公示系统」或「爱企查」搜索公司全称",
            "② 登记信息：看注册资本；若有实缴/认缴明细一并查看",
            "③ 进入该企业 →「年度报告」→ 最新一年",
            "④ 找到「社会保险」→ 看「城镇职工基本养老保险参保人数」",
            "⑤ 对照下方核对清单自行判断",
            "",
            "已可点击「打开免费查询」在浏览器中搜索该公司。",
        ],
        flags=["【核对清单】"] + [f"□ {item}" for item in FREE_CHECKLIST],
        risk_level="待你核对",
    )
    return profile


def _query_tianyancha(name: str) -> CompanyProfile:
    cfg = load_api_config()
    token = (cfg.get("token") or "").strip()
    url = f"{TIANYANCHA_BASEINFO}?keyword={urllib.parse.quote(name)}"
    req = urllib.request.Request(url, headers={"Authorization": token})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        raise RuntimeError(f"天眼查请求失败 HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"网络错误: {e.reason}") from e

    if data.get("error_code") != 0:
        raise RuntimeError(f"天眼查返回错误: {data.get('reason') or '未知'}")

    r = data.get("result") or {}
    profile = CompanyProfile(
        name=r.get("name") or name,
        reg_status=r.get("regStatus"),
        reg_capital=r.get("regCapital"),
        actual_capital=r.get("actualCapital"),
        social_staff_num=_to_int(r.get("socialStaffNum")),
        staff_num_range=r.get("staffNumRange"),
        legal_person=r.get("legalPersonName"),
        credit_code=r.get("creditCode"),
        reg_location=r.get("regLocation"),
        estiblish_time=_fmt_time(r.get("estiblishTime")),
        source="tianyancha",
        manual_links=manual_search_links(name),
        check_guide=[],
    )
    profile.flags = _assess_flags(profile)
    profile.risk_level = _company_risk_level(profile.flags)
    return profile


def profile_to_dict(p: CompanyProfile) -> dict:
    urls = platform_urls(p.name)
    return {
        "name": p.name,
        "platform_urls": urls,
        "reg_status": p.reg_status,
        "reg_capital": p.reg_capital,
        "actual_capital": p.actual_capital,
        "social_staff_num": p.social_staff_num,
        "staff_num_range": p.staff_num_range,
        "legal_person": p.legal_person,
        "credit_code": p.credit_code,
        "reg_location": p.reg_location,
        "establish_time": p.estiblish_time,
        "flags": p.flags,
        "risk_level": p.risk_level,
        "source": p.source,
        "check_guide": p.check_guide,
        "manual_links": p.manual_links or manual_search_links(p.name),
        "error": p.raw_error,
        "is_free_mode": p.source == "free_manual",
    }


def _to_int(v) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _fmt_time(ts) -> str | None:
    if not ts:
        return None
    try:
        from datetime import datetime

        return datetime.fromtimestamp(int(ts) / 1000).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return str(ts)


def _is_empty_capital(val: str | None) -> bool:
    if not val:
        return True
    s = val.strip().replace(" ", "")
    if s in ("-", "—", "0", "0万", "0万元", "未公示", "无"):
        return True
    if re.match(r"^0+(\.\d+)?万", s):
        return True
    return False


def _assess_flags(p: CompanyProfile) -> list[str]:
    flags: list[str] = []
    status = (p.reg_status or "").strip()
    if status and status not in ("存续", "在业", "开业", "仍注册"):
        flags.append(f"经营状态异常：{status}")
    if _is_empty_capital(p.actual_capital):
        flags.append("实缴资本为空或未公示（疑似空壳）")
    if p.social_staff_num is not None:
        if p.social_staff_num == 0:
            flags.append("参保人数为 0")
        elif p.social_staff_num < 5:
            flags.append(f"参保人数过少（{p.social_staff_num} 人）")
    else:
        flags.append("未获取到参保人数")
    if p.reg_capital and not _is_empty_capital(p.reg_capital) and _is_empty_capital(p.actual_capital):
        flags.append("有注册资本但无实缴信息")
    if not flags:
        flags.append("工商数据未见明显异常（仍需结合招聘话术判断）")
    return flags


def _company_risk_level(flags: list[str]) -> str:
    if any("为 0" in f or "异常" in f or "空壳" in f for f in flags):
        return "高危"
    if any("过少" in f for f in flags):
        return "中危"
    if flags and "未见明显异常" in flags[0]:
        return "低危"
    return "中危"
