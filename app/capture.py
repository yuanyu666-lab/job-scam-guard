"""高清区域截图（适配 Windows 高 DPI）。"""

from __future__ import annotations

from PIL import Image


def grab_bbox(bbox: tuple[int, int, int, int]) -> Image.Image:
    left, top, right, bottom = bbox
    width = max(1, right - left)
    height = max(1, bottom - top)

    try:
        import mss

        with mss.mss() as sct:
            shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
            return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    except Exception:
        from PIL import ImageGrab

        return ImageGrab.grab(bbox=bbox).convert("RGB")
