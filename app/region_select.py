"""全屏框选区域（类似截图工具）。"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

OVERLAY_BG = "#000000"
OVERLAY_ALPHA = 0.45
SEL_FILL = "#3b82f6"
SEL_OUTLINE = "#60a5fa"
MIN_SIZE = 24


class RegionSelector:
    def __init__(
        self,
        parent: tk.Tk,
        on_done: Callable[[tuple[int, int, int, int]], None],
        on_cancel: Callable[[], None],
    ) -> None:
        self.on_done = on_done
        self.on_cancel = on_cancel
        self.start_x = 0
        self.start_y = 0
        self.rect_id: int | None = None

        self.win = tk.Toplevel(parent)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", OVERLAY_ALPHA)
        self.win.configure(bg=OVERLAY_BG, cursor="crosshair")

        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.geometry(f"{sw}x{sh}+0+0")

        self.canvas = tk.Canvas(self.win, bg=OVERLAY_BG, highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.create_text(
            sw // 2,
            48,
            text="框选整块文字区域（尽量大、贴紧）· Esc 取消",
            fill="white",
            font=("Microsoft YaHei UI", 14, "bold"),
        )

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.win.bind("<Escape>", lambda _: self._cancel())
        self.win.focus_force()

    def _on_press(self, event: tk.Event) -> None:
        self.start_x, self.start_y = event.x_root, event.y_root
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline=SEL_OUTLINE,
            width=2,
            fill=SEL_FILL,
            stipple="gray50",
        )

    def _on_drag(self, event: tk.Event) -> None:
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x_root, event.y_root)

    def _on_release(self, event: tk.Event) -> None:
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x_root, event.y_root
        left, top = min(x1, x2), min(y1, y2)
        right, bottom = max(x1, x2), max(y1, y2)
        self.win.destroy()
        if right - left < MIN_SIZE or bottom - top < MIN_SIZE:
            self.on_cancel()
            return
        self.on_done((left, top, right, bottom))

    def _cancel(self) -> None:
        self.win.destroy()
        self.on_cancel()
