"""
截图 OCR（本地）

引擎优先级（auto）：
1. PaddleOCR 3 + PP-OCRv5（中文最强开源，需额外安装）
2. RapidOCR（PP-OCR ONNX，轻量，推荐）
3. Windows 系统 OCR（备用）
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "ocr_config.json"
OCR_TIMEOUT_SEC = 60

_paddle_engine: Any = None
_paddle_unavailable: bool | None = None
_rapid_engine: Any = None
_rapid_unavailable: bool | None = None


def get_ocr_status() -> dict:
    return {
        "paddle": _paddle_available(),
        "rapid": _rapid_available(),
        "windows": True,
        "preferred": _pick_engines()[0][1] if _pick_engines() else "无",
    }


def image_to_text(img: Image.Image) -> tuple[str, str]:
    if img.width < 8 or img.height < 8:
        raise ValueError("选区太小，请框选更大区域")

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run_ocr, img)
        try:
            return future.result(timeout=OCR_TIMEOUT_SEC)
        except FuturesTimeout:
            raise RuntimeError(
                f"识别超过 {OCR_TIMEOUT_SEC} 秒。请缩小框选，或改用「粘贴检测」（不经过 OCR）。"
            )


def _load_engine_pref() -> str:
    try:
        from app.settings import get_ocr_engine_pref

        return get_ocr_engine_pref()
    except ImportError:
        pass
    if not CONFIG_PATH.exists():
        return "auto"
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return (json.load(f).get("engine") or "auto").lower()


def _pick_engines() -> list[tuple[Callable[[Image.Image], str], str]]:
    pref = _load_engine_pref()
    all_engines: list[tuple[Callable[[Image.Image], str], str]] = []

    if pref == "fast":
        if _rapid_available():
            all_engines.append((_ocr_rapid, "RapidOCR"))
        all_engines.append((_ocr_windows, "Windows OCR"))
        return all_engines

    if pref in ("auto", "paddle") and _paddle_available():
        all_engines.append((_ocr_paddle, "PaddleOCR PP-OCRv5"))
    if pref in ("auto", "rapid") and _rapid_available():
        all_engines.append((_ocr_rapid, "RapidOCR"))
    if pref in ("auto", "windows"):
        all_engines.append((_ocr_windows, "Windows OCR"))

    if pref == "paddle" and not _paddle_available():
        pass
    elif pref == "rapid" and not _rapid_available():
        pass

    if not all_engines:
        if _rapid_available():
            all_engines.append((_ocr_rapid, "RapidOCR"))
        all_engines.append((_ocr_windows, "Windows OCR"))
    return all_engines


def _run_ocr(img: Image.Image) -> tuple[str, str]:
    variants = _preprocess_variants(img)
    engines = _pick_engines()
    errors: list[str] = []
    best_text = ""
    best_engine = ""

    # 先用主引擎 + 最佳预处理图（快）
    primary_img = variants[0][1]
    for ocr_fn, name in engines:
        try:
            text = ocr_fn(primary_img)
            if len(text) > len(best_text):
                best_text, best_engine = text, name
            if len(text) >= 30:
                return text, name
        except Exception as exc:
            errors.append(f"{name}:{exc}")

    # 再试所有预处理图，取最长结果
    for tag, variant in variants:
        for ocr_fn, name in engines:
            try:
                text = ocr_fn(variant)
                if len(text) > len(best_text):
                    best_text, best_engine = text, f"{name}({tag})"
            except Exception as exc:
                if name not in str(errors):
                    errors.append(f"{name}:{exc}")

    if best_text:
        return best_text, best_engine

    raise RuntimeError(
        "无法识别文字。请重启程序等待模型加载完成，或改用「粘贴检测」。\n"
        f"详情：{errors[-1] if errors else '无可用引擎'}"
    )


def _preprocess_variants(img: Image.Image) -> list[tuple[str, Image.Image]]:
    base = img.convert("RGB")
    w, h = base.size
    scale = 2 if max(w, h) < 900 else 1.5 if max(w, h) < 1400 else 1.0
    if scale > 1:
        base = base.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    color = ImageEnhance.Contrast(base).enhance(1.35)
    color = ImageEnhance.Sharpness(color).enhance(1.6)
    color = color.filter(ImageFilter.SHARPEN)
    gray_rgb = ImageOps.autocontrast(ImageOps.grayscale(color)).convert("RGB")

    return [("增强", color), ("灰度", gray_rgb), ("放大", base)]


def _paddle_available() -> bool:
    global _paddle_unavailable
    if _paddle_unavailable is True:
        return False
    try:
        import paddleocr  # noqa: F401

        return True
    except ImportError:
        _paddle_unavailable = True
        return False


def _rapid_available() -> bool:
    global _rapid_unavailable
    if _rapid_unavailable is True:
        return False
    try:
        import rapidocr_onnxruntime  # noqa: F401

        return True
    except ImportError:
        _rapid_unavailable = True
        return False


def _get_paddle():
    global _paddle_engine
    if _paddle_engine is None:
        from paddleocr import PaddleOCR

        _paddle_engine = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="PP-OCRv5_mobile_rec",
        )
    return _paddle_engine


def _get_rapid():
    global _rapid_engine
    if _rapid_engine is None:
        from rapidocr_onnxruntime import RapidOCR

        _rapid_engine = RapidOCR()
    return _rapid_engine


def _ocr_paddle(img: Image.Image) -> str:
    import numpy as np
    import tempfile

    engine = _get_paddle()
    arr = np.array(img)

    # PaddleOCR 3 支持 predict；旧版支持 ocr()
    if hasattr(engine, "predict"):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img.save(tmp.name)
            path = tmp.name
        try:
            result = engine.predict(path)
        finally:
            Path(path).unlink(missing_ok=True)
        return _extract_paddle_v3(result)

    result = engine.ocr(arr, cls=False)
    lines: list[str] = []
    for block in result or []:
        for line in block or []:
            if line and len(line) > 1:
                lines.append(str(line[1][0]))
    return _clean("\n".join(lines))


def _extract_paddle_v3(result: Any) -> str:
    texts: list[str] = []
    for res in result or []:
        data = None
        if hasattr(res, "json"):
            data = res.json() if callable(res.json) else res.json
        elif isinstance(res, dict):
            data = res
        if not data:
            continue
        inner = data.get("res", data)
        rec = inner.get("rec_texts") or inner.get("rec_text")
        if isinstance(rec, list):
            texts.extend(str(t) for t in rec if t)
        elif rec:
            texts.append(str(rec))
    return _clean("\n".join(texts))


def _ocr_rapid(img: Image.Image) -> str:
    import numpy as np

    result, _ = _get_rapid()(np.array(img))
    if not result:
        return ""
    lines = [str(item[1]).strip() for item in result if item and len(item) > 1]
    return _clean("\n".join(lines))


def _ocr_windows(img: Image.Image) -> str:
    from winocr import recognize_pil_sync

    return _parse_winocr(recognize_pil_sync(img, lang="zh-Hans"))


def _parse_winocr(raw: Any) -> str:
    if isinstance(raw, str):
        return _clean(raw)
    if isinstance(raw, dict):
        text = raw.get("text") or ""
        if isinstance(text, str) and text.strip():
            return _clean(text)
        parts: list[str] = []
        for line in raw.get("lines") or []:
            if isinstance(line, dict) and line.get("text"):
                parts.append(str(line["text"]).strip())
            elif isinstance(line, str) and line.strip():
                parts.append(line.strip())
        if parts:
            return _clean("\n".join(parts))
    return ""


def _clean(text: str) -> str:
    from app.company import collapse_cjk_spaces

    text = collapse_cjk_spaces(text.replace("\r", ""))
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    return "\n".join(lines)
