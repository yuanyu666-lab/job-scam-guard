"""图片 OCR + 招聘风险分析（供手机端上传）。"""

from __future__ import annotations

import io

from PIL import Image

from app.analyze_service import analyze_full
from app.ocr import image_to_text


def analyze_image_bytes(
    data: bytes,
    *,
    content_type: str = "auto",
    use_ai: bool | None = None,
    provider: str | None = None,
) -> dict:
    if len(data) > 12 * 1024 * 1024:
        raise ValueError("图片过大（上限 12MB）")
    img = Image.open(io.BytesIO(data))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    text, engine = image_to_text(img)
    stripped = text.strip()
    if len(stripped) < 4:
        raise ValueError("未识别到足够文字，请框选更大、更清晰区域")
    result = analyze_full(
        stripped,
        content_type,
        use_ai=use_ai,
        provider=provider,
        save_history=False,
        apply_ocr_fix=True,
    )
    result["ocr_engine"] = engine
    result["ocr_char_count"] = len(stripped)
    result["ocr_text_preview"] = stripped[:800]
    return result
