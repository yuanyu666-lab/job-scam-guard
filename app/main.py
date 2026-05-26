"""招聘防骗系统 — 个人本地服务。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.company import (
    extract_company_names,
    is_configured,
    profile_to_dict,
    query_company,
)
from app.analyze_service import analyze_full
from app.engine import analyze_text, check_url, get_config, init_patterns, reload_patterns, result_to_dict
from app.ai_router import is_provider_configured, load_ai_config, resolve_provider
from app.history import export_history_markdown, list_history, search_history
from app.settings import get_settings, save_settings_patch
from app.checklist import build_verification_checklist
from app.feedback import append_feedback
from app.image_analyze import analyze_image_bytes
from app.mobile_auth import load_mobile_api_config, mobile_api_enabled, verify_api_key
from app.deepseek import is_configured as deepseek_configured, load_config as load_deepseek_config
from app.gemini import is_configured as gemini_configured, load_config as load_gemini_config

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
NOTES_FILE = ROOT / "data" / "notes.jsonl"

app = FastAPI(title="招聘防骗", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    content_type: str = "auto"
    use_ai: bool | None = None
    provider: str | None = Field(None, pattern="^(gemini|deepseek|none)$")


class UrlCheckRequest(BaseModel):
    url: str = Field(..., min_length=3, max_length=2000)


class NoteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    note: str | None = Field(None, max_length=500)


class CompanyRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)


class SettingsPatch(BaseModel):
    strict_mode: bool | None = None
    strict_ai_trigger: str | None = None
    ocr_engine: str | None = None
    save_history: bool | None = None
    ocr_post_fix: bool | None = None
    enabled_platform_packs: list[str] | None = None
    history_max: int | None = None


class FeedbackRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    label: str = Field("false_positive", pattern="^(false_positive|false_negative|other)$")
    comment: str = Field("", max_length=500)
    result: dict | None = None


@app.on_event("startup")
def startup():
    init_patterns()
    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)


@app.get("/api/health")
def health():
    cfg = get_config()
    gcfg = load_gemini_config()
    return {
        "status": "ok",
        "rules": len(cfg["categories"]),
        "notes_file": str(NOTES_FILE),
        "company_api": is_configured(),
        "gemini": gemini_configured(),
        "deepseek": deepseek_configured(),
        "ai_provider": resolve_provider(),
        "gemini_model": gcfg.get("model") if gemini_configured() else None,
        "deepseek_model": load_deepseek_config().get("model")
        if deepseek_configured()
        else None,
        "settings": {
            "auto_content_type": get_settings().get("auto_content_type", True),
            "ocr_engine": get_settings().get("ocr_engine", "fast"),
        },
    }


@app.get("/api/company/status")
def company_status():
    return {
        "configured": is_configured(),
        "default_mode": "free",
        "paid_provider": "tianyancha（需在 company_api.json 开启 use_paid_api）",
    }


@app.post("/api/company")
def company_lookup(req: CompanyRequest, paid: bool = False):
    try:
        profile = query_company(req.name.strip(), paid=paid)
        return {"ok": True, **profile_to_dict(profile)}
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e


class CompanyOpenRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    platform: str = Field("tianyancha", pattern="^(tianyancha|qcc|aiqicha|gsxt)$")


@app.get("/api/company/links")
def company_links(name: str):
    from app.company import platform_urls

    n = name.strip()
    if len(n) < 2:
        raise HTTPException(400, "公司名过短")
    return {"name": n, "urls": platform_urls(n)}


@app.post("/api/company/open")
def company_open(req: CompanyOpenRequest):
    from app.company import open_platform

    try:
        url = open_platform(req.name.strip(), req.platform)
        return {"ok": True, "platform": req.platform, "opened": url}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/company/from-text")
def company_from_text(req: AnalyzeRequest):
    """从文本提取公司名，返回各平台跳转链接。"""
    from app.company import platform_urls

    names = extract_company_names(req.text.strip())
    if not names:
        return {"ok": False, "message": "未识别到公司名称", "candidates": []}
    primary = names[0]
    return {
        "ok": True,
        "candidates": names,
        "primary": primary,
        "urls": platform_urls(primary),
        "tip": "点击天眼查/企查查，在网页中查看实缴资本与参保人数",
    }


@app.get("/api/gemini/status")
def gemini_status():
    cfg = load_gemini_config()
    return {
        "configured": gemini_configured(),
        "model": cfg.get("model"),
        "allow_fallback": cfg.get("allow_fallback", False),
        "use_on_analyze": cfg.get("use_on_analyze", True),
        "setup": "复制 data/gemini_config.json.example 为 gemini_config.json 并填写 api_key",
        "billing_note": "网页版 Gemini Pro 与 API 计费分开；需在 AI Studio 为 Key 所在项目开通 Billing",
    }


@app.get("/api/ai/status")
def ai_status():
    acfg = load_ai_config()
    gcfg = load_gemini_config()
    dcfg = load_deepseek_config()
    return {
        "provider": resolve_provider(),
        "gemini": {
            "configured": gemini_configured(),
            "model": gcfg.get("model"),
        },
        "deepseek": {
            "configured": deepseek_configured(),
            "model": dcfg.get("model"),
        },
        "setup": {
            "ai": "复制 data/ai_config.json.example → ai_config.json",
            "deepseek": "复制 data/deepseek_config.json.example → deepseek_config.json",
            "gemini": "复制 data/gemini_config.json.example → gemini_config.json",
        },
    }


@app.post("/api/gemini/test")
def gemini_test():
    """探测 Gemini Key（会消耗少量额度）。"""
    from app.ai_insight import insight_to_dict
    from app.gemini import analyze_with_gemini

    sample = "日结300 加微信 17-22岁 打字文员 小白"
    rule = analyze_text(sample, "chat")
    return insight_to_dict(analyze_with_gemini(sample, "chat", rule))


@app.post("/api/deepseek/test")
def deepseek_test():
    """探测 DeepSeek Key（会消耗少量额度）。"""
    from app.ai_insight import insight_to_dict
    from app.deepseek import analyze_with_deepseek

    sample = "日结300 加微信 17-22岁 打字文员 小白"
    rule = analyze_text(sample, "chat")
    return insight_to_dict(analyze_with_deepseek(sample, "chat", rule))


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest, x_api_key: str | None = Header(None, alias="X-API-Key")):
    verify_api_key(x_api_key)
    return analyze_full(
        req.text.strip(),
        req.content_type,
        use_ai=req.use_ai,
        provider=req.provider,
    )


@app.post("/api/analyze/image")
async def analyze_image(
    file: UploadFile = File(...),
    content_type: str = "auto",
    use_ai: bool | None = None,
    provider: str | None = None,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
):
    """手机悬浮框选后上传截图：服务端 OCR + 风险分析。"""
    verify_api_key(x_api_key)
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(400, "请上传图片文件")
    data = await file.read()
    try:
        return analyze_image_bytes(
            data,
            content_type=content_type,
            use_ai=use_ai,
            provider=provider,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/mobile/status")
def mobile_status():
    cfg = load_mobile_api_config()
    return {
        "ok": True,
        "auth_required": mobile_api_enabled(),
        "max_image_mb": 12,
        "endpoints": {
            "analyze_text": "POST /api/analyze",
            "analyze_image": "POST /api/analyze/image",
        },
        "note": "需将服务部署到公网 HTTPS，手机 App 配置该地址",
    }


@app.get("/mobile")
def mobile_page():
    path = STATIC / "mobile.html"
    if not path.exists():
        raise HTTPException(404, "mobile.html 未找到")
    return FileResponse(path)


@app.get("/api/history")
def history(limit: int = 10, q: str | None = None):
    if q and q.strip():
        return {"items": search_history(q.strip(), limit=min(max(limit, 1), 50))}
    return {"items": list_history(limit=min(max(limit, 1), 30))}


@app.get("/api/history/export")
def history_export(limit: int = 20):
    return {"markdown": export_history_markdown(limit=min(max(limit, 1), 50))}


@app.get("/api/settings")
def settings_get():
    return get_settings()


@app.patch("/api/settings")
def settings_patch(req: SettingsPatch):
    patch = {k: v for k, v in req.model_dump().items() if v is not None}
    return save_settings_patch(patch)


@app.post("/api/patterns/reload")
def patterns_reload():
    return reload_patterns()


@app.post("/api/feedback")
def feedback_post(req: FeedbackRequest):
    result = req.result or analyze_full(
        req.text.strip(), "auto", use_ai=False, provider="none", save_history=False
    )
    entry = append_feedback(req.text.strip(), result, label=req.label, comment=req.comment)
    return {"ok": True, "entry": entry}


@app.post("/api/checklist")
def checklist_from_text(req: AnalyzeRequest):
    r = analyze_full(
        req.text.strip(),
        req.content_type,
        use_ai=req.use_ai,
        provider=req.provider,
        save_history=False,
    )
    return {"text": build_verification_checklist(req.text.strip(), r)}


@app.post("/api/analyze/url")
def analyze_url(req: UrlCheckRequest):
    warning = check_url(req.url.strip(), get_config())
    score = 30 if warning else 8
    return {
        "url": req.url,
        "risk_score": score,
        "risk_level": "高危" if warning else "低危",
        "warning": warning,
        "safe": warning is None,
    }


@app.post("/api/note")
def save_note(req: NoteRequest):
    """记下可疑条目，仅追加到本地文件。"""
    analysis = analyze_text(req.text.strip(), "general")
    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "risk_score": analysis.risk_score,
        "risk_level": analysis.risk_level,
        "note": req.note,
        "preview": req.text[:120],
    }
    with open(NOTES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"ok": True, **entry}


@app.get("/api/notes")
def list_notes(limit: int = 10):
    if not NOTES_FILE.exists():
        return {"notes": []}
    lines = NOTES_FILE.read_text(encoding="utf-8").strip().splitlines()
    items = [json.loads(line) for line in lines[-limit:] if line.strip()]
    return {"notes": list(reversed(items))}


@app.get("/")
def index():
    path = STATIC / "index.html"
    if not path.exists():
        raise HTTPException(404, "前端未找到")
    return FileResponse(path)


if STATIC.exists():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
