"""
招聘防骗 — 悬浮窗 + 框选识图
双击悬浮球：全屏框选 → OCR → 自动风险检测
"""

from __future__ import annotations

import ctypes
import sys
import threading
import tkinter as tk
from ctypes import wintypes
from tkinter import messagebox, scrolledtext, ttk

from app.capture import grab_bbox
from app.company import (
    best_company_name,
    extract_company_names,
    is_plausible_company_name,
    normalize_company_name,
    open_platform,
)
from app.analyze_service import analyze_full
from app.ai_router import is_provider_configured, load_ai_config
from app.checklist import build_verification_checklist
from app.deepseek import is_configured as deepseek_ready
from app.engine import init_patterns, reload_patterns
from app.feedback import append_feedback
from app.gemini import is_configured as gemini_ready
from app.history import export_history_markdown, list_history
from app.ocr import image_to_text
from app.region_select import RegionSelector
from app.settings import get_settings, save_settings_patch, save_ui_state
from app.summary import display_risk_level

# —— 主题色 ——
BG = "#0a0e14"
PANEL = "#121a24"
CARD = "#182230"
BORDER = "#263244"
BORDER_HI = "#3d5168"
TEXT = "#eef2f7"
MUTED = "#8b9cb3"
ACCENT = "#4d8dff"
ACCENT_HOVER = "#6ba3ff"
RING = "#1e3a5f"
LOW, MID, HIGH = "#34d399", "#fbbf24", "#f87171"
LOW_BG, MID_BG, HIGH_BG = "#0d2e22", "#2e2410", "#2e1518"

FONT = "Microsoft YaHei UI"
BALL = 58
EXPAND_W, EXPAND_H = 420, 720
HOTKEY_ID = 1
PAD = 16
GAP = 10
INNER = 12
SUBTEXT = "#c8d4e3"
TEXT_WRAP = EXPAND_W - PAD * 2 - INNER * 2 - 20


def _bind_drag(widgets: tuple, start, move) -> None:
    for w in widgets:
        w.bind("<Button-1>", start)
        w.bind("<B1-Motion>", move)


def _enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class FloatGuard:
    def _btn(
        self,
        parent: tk.Misc,
        text: str,
        command,
        *,
        primary: bool = False,
        small: bool = False,
        ghost: bool = False,
        color: str | None = None,
    ) -> tk.Button:
        if color:
            bg, fg, active = color, "white", color
        elif primary:
            bg, fg, active = ACCENT, "white", ACCENT_HOVER
        elif ghost:
            bg, fg, active = PANEL, MUTED, CARD
        else:
            bg, fg, active = CARD, TEXT, BORDER_HI
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active,
            activeforeground="white" if primary else TEXT,
            bd=0,
            padx=16 if primary else (12 if not small else 8),
            pady=9 if primary else (7 if not small else 5),
            cursor="hand2",
            font=(FONT, 9, "bold" if primary else "normal"),
            relief="flat",
            highlightthickness=1 if ghost else 0,
            highlightbackground=BORDER if ghost else bg,
            highlightcolor=BORDER_HI if ghost else bg,
        )

    def _section_title(self, parent: tk.Misc, text: str) -> None:
        tk.Label(
            parent,
            text=text,
            font=(FONT, 8),
            fg=MUTED,
            bg=CARD,
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

    def _card(self, parent: tk.Misc, *, pack: bool = True, **pack_kw) -> tk.Frame:
        f = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        if not pack:
            return f
        opts: dict = {"fill": "x", "padx": PAD, "pady": (0, GAP)}
        opts.update(pack_kw)
        f.pack(**opts)
        return f

    def _entry(self, parent: tk.Misc) -> tk.Entry:
        return tk.Entry(
            parent,
            font=(FONT, 9),
            bg=BG,
            fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )

    def _text(self, parent: tk.Misc, *, height: int, disabled: bool = False) -> scrolledtext.ScrolledText:
        w = scrolledtext.ScrolledText(
            parent,
            height=height,
            font=(FONT, 10),
            bg=BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            wrap="word",
            padx=8,
            pady=8,
            state="disabled" if disabled else "normal",
        )
        try:
            w.configure(selectbackground=ACCENT, selectforeground="white")
        except tk.TclError:
            pass
        return w

    def __init__(self) -> None:
        init_patterns()
        self.expanded = False
        self._analyzing = False
        self._drag: tuple[int, int] | None = None
        self._moved = False
        self._selecting = False
        self._history_items: list[dict] = []
        self._last_result: dict | None = None
        self._last_text: str = ""
        self._settings_win: tk.Toplevel | None = None
        self._exiting = False

        self.root = tk.Tk()
        self.root.title("招聘防骗")
        self.root.configure(bg=BG)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.96)
        self.root.resizable(False, False)

        sw = self.root.winfo_screenwidth()
        ux, uy, umode = self._load_ui_position(sw)
        w0 = EXPAND_W if umode == "panel" else BALL
        h0 = EXPAND_H if umode == "panel" else BALL
        self.root.geometry(f"{w0}x{h0}+{ux}+{uy}")

        self._build_ball()
        self._build_panel()
        self._configure_ttk()
        if umode == "panel":
            self._show_panel()
        else:
            self._show_ball()

        self.root.bind("<Escape>", self._on_escape)
        self.root.protocol("WM_DELETE_WINDOW", self._quit_app)
        self._register_hotkey()
        self.root.after(80, self._poll_hotkey)
        self.root.after(200, self._refresh_history)

    def _build_ball(self) -> None:
        self.ball = tk.Frame(
            self.root,
            bg=RING,
            width=BALL + 4,
            height=BALL + 4,
        )
        self.ball.pack_propagate(False)
        inner = tk.Frame(self.ball, bg=ACCENT, width=BALL, height=BALL)
        inner.place(relx=0.5, rely=0.5, anchor="center")
        inner.pack_propagate(False)
        lbl = tk.Label(
            inner,
            text="盾",
            font=(FONT, 20, "bold"),
            fg="white",
            bg=ACCENT,
            cursor="hand2",
        )
        lbl.pack(expand=True)
        tip = tk.Label(
            inner,
            text="双击框选",
            font=(FONT, 7),
            fg="#dbeafe",
            bg=ACCENT,
        )
        tip.pack(side="bottom", pady=(0, 5))
        drag_targets = (self.ball, inner, lbl, tip)
        for w in drag_targets:
            w.bind("<ButtonRelease-1>", self._end_drag)
            w.bind("<Double-Button-1>", lambda _: self._start_snip())
            w.bind("<Button-3>", self._context_menu)
        _bind_drag(drag_targets, self._start_drag, self._on_drag)

    def _configure_ttk(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Guard.Horizontal.TProgressbar",
            troughcolor=BORDER,
            background=ACCENT,
            bordercolor=BORDER,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            thickness=3,
        )

    def _build_panel(self) -> None:
        self.panel = tk.Frame(
            self.root,
            bg=PANEL,
            width=EXPAND_W,
            height=EXPAND_H,
            highlightthickness=1,
            highlightbackground=BORDER,
        )

        # —— 顶栏 ——
        title = tk.Frame(self.panel, bg=PANEL)
        title.pack(fill="x", padx=PAD, pady=(14, 0))
        brand = tk.Frame(title, bg=PANEL)
        brand.pack(side="left")
        tk.Label(brand, text="🛡", font=(FONT, 14), fg=ACCENT, bg=PANEL).pack(side="left")
        title_lbl = tk.Label(
            brand, text=" 招聘防骗", font=(FONT, 12, "bold"), fg=TEXT, bg=PANEL
        )
        title_lbl.pack(side="left")
        _bind_drag((title, brand, title_lbl), self._start_drag, self._on_drag)

        close_btn = tk.Button(
            title,
            text="✕",
            command=self._quit_app,
            bg=PANEL,
            fg=MUTED,
            activebackground=CARD,
            activeforeground=TEXT,
            bd=0,
            width=2,
            cursor="hand2",
            font=(FONT, 11),
            relief="flat",
        )
        close_btn.pack(side="right")
        settings_btn = tk.Button(
            title,
            text="⚙",
            command=self._open_settings,
            bg=PANEL,
            fg=MUTED,
            activebackground=CARD,
            activeforeground=TEXT,
            bd=0,
            width=2,
            cursor="hand2",
            font=(FONT, 11),
            relief="flat",
        )
        settings_btn.pack(side="right", padx=(0, 4))

        # —— 状态行（类型 + 提示合一）——
        meta = tk.Frame(self.panel, bg=PANEL)
        meta.pack(fill="x", padx=PAD, pady=(10, GAP))
        self.meta_frame = meta
        self.type_badge = tk.Label(
            meta,
            text="自动识别",
            font=(FONT, 8),
            fg=ACCENT,
            bg=CARD,
            padx=8,
            pady=3,
        )
        self.type_badge.pack(side="left")
        self.type_label = self.type_badge
        self.status_label = tk.Label(
            meta,
            text="粘贴或框选内容开始",
            font=(FONT, 8),
            fg=MUTED,
            bg=PANEL,
            anchor="e",
        )
        self.status_label.pack(side="right", fill="x", expand=True, padx=(10, 0))

        self.progress = ttk.Progressbar(
            self.panel,
            mode="indeterminate",
            length=EXPAND_W - PAD * 2,
            style="Guard.Horizontal.TProgressbar",
        )

        self.history_frame = tk.Frame(self.panel, bg=PANEL)

        # —— 先构建底部固定区（企业 + AI + 脚注），再 pack 时用 side=bottom 钉住 ——
        self.footer_label = tk.Label(
            self.panel,
            text="双击悬浮球框选  ·  Ctrl+Alt+J  ·  Esc 收起  ·  ✕ 退出",
            font=(FONT, 7),
            fg=MUTED,
            bg=PANEL,
        )

        self.ai_row = tk.Frame(self.panel, bg=PANEL)
        tk.Label(self.ai_row, text="AI", font=(FONT, 8), fg=MUTED, bg=PANEL).pack(side="left")
        self.ai_provider = tk.StringVar(value=self._default_ai_provider())
        self._ai_pills: dict[str, tk.Radiobutton] = {}
        pill_row = tk.Frame(self.ai_row, bg=PANEL)
        pill_row.pack(side="left", padx=(8, 0))
        for val, label in (("none", "关"), ("deepseek", "DS"), ("gemini", "GM")):
            rb = tk.Radiobutton(
                pill_row,
                text=label,
                variable=self.ai_provider,
                value=val,
                indicatoron=0,
                padx=10,
                pady=4,
                bg=CARD,
                fg=MUTED,
                selectcolor=ACCENT,
                activebackground=ACCENT,
                activeforeground="white",
                font=(FONT, 8),
                bd=0,
                highlightthickness=0,
                cursor="hand2",
            )
            rb.pack(side="left", padx=(0, 4))
            self._ai_pills[val] = rb
        self.ai_provider.trace_add("write", lambda *_: self._refresh_ai_pills())
        self._refresh_ai_pills()
        self.ai_decision_label = tk.Label(
            self.ai_row,
            text="",
            font=(FONT, 7),
            fg=MUTED,
            bg=PANEL,
            wraplength=EXPAND_W - PAD * 2 - 80,
            justify="left",
        )
        self.ai_decision_label.pack(side="bottom", fill="x", pady=(4, 0))
        hints = []
        if deepseek_ready():
            hints.append("DeepSeek")
        if gemini_ready():
            hints.append("Gemini")
        tk.Label(
            self.ai_row,
            text=" · ".join(hints) if hints else "未配置 Key",
            font=(FONT, 7),
            fg=LOW if hints else MUTED,
            bg=PANEL,
        ).pack(side="right")

        self.co_card = self._card(self.panel, pack=False)
        co_inner = tk.Frame(self.co_card, bg=CARD)
        co_inner.pack(fill="x", padx=INNER, pady=INNER)
        self._section_title(co_inner, "企业核实")
        self.company_input = self._entry(co_inner)
        self.company_input.pack(fill="x", pady=(0, 4))
        self.company_input.bind("<KeyRelease>", lambda _: self._sync_company_hint())
        co_btns = tk.Frame(co_inner, bg=CARD)
        co_btns.pack(fill="x")
        self._btn(co_btns, "双开查询", self._open_both_platforms, small=True, ghost=True).pack(
            side="left", expand=True, fill="x", padx=(0, 5)
        )
        self._btn(
            co_btns,
            "天眼查",
            lambda: self._open_platform("tianyancha"),
            small=True,
            ghost=True,
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))
        self._btn(
            co_btns,
            "企查查",
            lambda: self._open_platform("qcc"),
            small=True,
            ghost=True,
        ).pack(side="left", expand=True, fill="x")
        co_btns2 = tk.Frame(co_inner, bg=CARD)
        co_btns2.pack(fill="x", pady=(6, 0))
        self._btn(
            co_btns2, "复制核查清单", self._copy_checklist, small=True, ghost=True
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))
        self._btn(
            co_btns2, "误报反馈", self._feedback_dialog, small=True, ghost=True
        ).pack(side="left", expand=True, fill="x")

        # —— 底部固定：先 pack，避免被结论区挤没 ——
        self.footer_label.pack(side="bottom", fill="x", pady=(0, 10))
        self.ai_row.pack(side="bottom", fill="x", padx=PAD, pady=(0, 8))
        self.co_card.pack(side="bottom", fill="x", padx=PAD, pady=(0, GAP))

        # —— 输入 ——
        in_card = self._card(self.panel)
        in_inner = tk.Frame(in_card, bg=CARD)
        in_inner.pack(fill="x", padx=INNER, pady=INNER)
        self._section_title(in_inner, "待检测内容")
        self.input_box = self._text(in_inner, height=4)
        self.input_box.pack(fill="x")

        # —— 主操作（两主一辅）——
        act_row = tk.Frame(self.panel, bg=PANEL)
        act_row.pack(fill="x", padx=PAD, pady=(0, GAP))
        self._btn(act_row, "框选识图", self._start_snip, ghost=True).pack(
            side="left", expand=True, fill="x", padx=(0, 6)
        )
        self._btn(act_row, "粘贴检测", self._paste_and_analyze, primary=True).pack(
            side="left", expand=True, fill="x", padx=(0, 6)
        )
        self._btn(act_row, "检测", self._analyze, ghost=True).pack(
            side="left", expand=True, fill="x"
        )

        # —— 结论 + 详情（仅占中间剩余高度，不挤压底部）——
        result_card = self._card(self.panel, pack=False)
        res_inner = tk.Frame(result_card, bg=CARD)
        res_inner.pack(fill="both", expand=True, padx=INNER, pady=INNER)

        self.score_band = tk.Frame(res_inner, bg=CARD, highlightthickness=0)
        self.score_band.pack(fill="x", pady=(0, 8))
        score_row = tk.Frame(self.score_band, bg=CARD)
        score_row.pack(fill="x", padx=10, pady=10)
        self.score_row = score_row
        self.score_left = score_row
        self.score_badge = tk.Label(
            score_row,
            text="待检测",
            font=(FONT, 11, "bold"),
            fg=MUTED,
            bg=BORDER,
            padx=12,
            pady=5,
        )
        self.score_badge.pack(anchor="w")
        self.headline_label = tk.Label(
            score_row,
            text="检测后将在此显示结论",
            font=(FONT, 10, "bold"),
            fg=TEXT,
            bg=CARD,
            wraplength=TEXT_WRAP,
            justify="left",
        )
        self.headline_label.pack(anchor="w", fill="x", pady=(10, 0))
        self.action_labels: list[tk.Label] = []
        for _ in range(2):
            al = tk.Label(
                score_row,
                text="",
                font=(FONT, 9),
                fg=SUBTEXT,
                bg=CARD,
                wraplength=TEXT_WRAP,
                justify="left",
            )
            al.pack(anchor="w", fill="x", pady=(6, 0))
            self.action_labels.append(al)

        detail_frame = tk.Frame(res_inner, bg=BG, highlightthickness=1, highlightbackground=BORDER)
        detail_frame.pack(fill="x")
        tk.Label(
            detail_frame,
            text="检测详情",
            font=(FONT, 8),
            fg=MUTED,
            bg=BG,
            anchor="w",
        ).pack(fill="x", padx=8, pady=(8, 4))
        self.result_box = self._text(detail_frame, height=4, disabled=True)
        self.result_box.configure(bg=BG, fg=TEXT)
        self.result_box.pack(fill="x", padx=6, pady=(0, 6))

        self.score_card = result_card
        self.score_inner = res_inner
        result_card.pack(fill="both", expand=True, padx=PAD, pady=(0, GAP))

    def _load_ui_position(self, sw: int) -> tuple[int, int, str]:
        if get_settings().get("remember_window_position", True):
            from app.settings import get_ui_geometry

            x, y, mode = get_ui_geometry()
            if x is not None and y is not None:
                return int(x), int(y), mode
        return sw - BALL - 48, 120, "ball"

    def _persist_ui_position(self) -> None:
        if not get_settings().get("remember_window_position", True):
            return
        mode = "panel" if self.expanded else "ball"
        save_ui_state(x=self.root.winfo_x(), y=self.root.winfo_y(), mode=mode)

    def _show_progress(self, on: bool) -> None:
        if on:
            self.progress.pack(
                fill="x", padx=PAD, pady=(0, GAP), after=self.meta_frame
            )
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.pack_forget()

    def _refresh_history(self) -> None:
        for w in self.history_frame.winfo_children():
            w.destroy()
        self._history_items = list_history(6)
        if not self._history_items:
            self.history_frame.pack_forget()
            return
        self.history_frame.pack(fill="x", padx=PAD, pady=(0, GAP))
        tk.Label(
            self.history_frame,
            text="最近",
            font=(FONT, 7),
            fg=MUTED,
            bg=PANEL,
        ).pack(side="left", padx=(0, 6))
        for i, item in enumerate(self._history_items):
            lvl = item.get("risk_level") or "?"
            sc = item.get("risk_score", "—")
            btn = tk.Button(
                self.history_frame,
                text=f"{lvl} {sc}",
                command=lambda idx=i: self._load_history(idx),
                bg=CARD,
                fg=MUTED,
                activebackground=BORDER_HI,
                activeforeground=TEXT,
                bd=0,
                padx=8,
                pady=3,
                cursor="hand2",
                font=(FONT, 7),
                relief="flat",
                highlightthickness=1,
                highlightbackground=BORDER,
            )
            btn.pack(side="left", padx=(0, 4))

    def _load_history(self, index: int) -> None:
        if index < 0 or index >= len(self._history_items):
            return
        item = self._history_items[index]
        text = item.get("text") or item.get("preview") or ""
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", text)
        self._expand()
        self._analyze()

    def _refresh_ai_pills(self) -> None:
        cur = self.ai_provider.get()
        for val, rb in self._ai_pills.items():
            if val == cur:
                rb.configure(bg=ACCENT, fg="white")
            else:
                rb.configure(bg=CARD, fg=MUTED)

    def _risk_display(self, level: str) -> str:
        return display_risk_level(level)

    def _apply_score_ui(self, level: str, label: str | None = None) -> None:
        if level in ("失败", "!"):
            fg, card_bg = HIGH, HIGH_BG
        elif level == "高危":
            fg, card_bg = HIGH, HIGH_BG
        elif level == "中危":
            fg, card_bg = MID, MID_BG
        else:
            fg, card_bg = LOW, LOW_BG
        self.score_card.configure(bg=CARD, highlightbackground=fg)
        self.score_band.configure(bg=card_bg, highlightbackground=fg, highlightthickness=1)
        for w in (self.score_row, self.headline_label, *self.action_labels):
            w.configure(bg=card_bg)
        self.score_badge.configure(
            text=label or self._risk_display(level), fg="white", bg=fg
        )
        self.headline_label.configure(fg=TEXT, bg=card_bg)
        for al in self.action_labels:
            al.configure(fg=SUBTEXT, bg=card_bg)

    def _show_ball(self) -> None:
        self.panel.pack_forget()
        self.ball.pack(fill="both", expand=True)
        self.expanded = False
        x, y = self.root.winfo_x(), self.root.winfo_y()
        self.root.geometry(f"{BALL}x{BALL}+{x}+{y}")
        self.root.deiconify()
        self._persist_ui_position()

    def _show_panel(self) -> None:
        self.ball.pack_forget()
        self.panel.pack(fill="both", expand=True)
        self.expanded = True
        x, y = self.root.winfo_x(), self.root.winfo_y()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        if x + EXPAND_W > sw:
            x = sw - EXPAND_W - 8
        if y + EXPAND_H > sh:
            y = max(0, sh - EXPAND_H - 8)
        self.root.geometry(f"{EXPAND_W}x{EXPAND_H}+{x}+{y}")
        self._persist_ui_position()

    def _expand(self) -> None:
        if not self.expanded:
            self._show_panel()
            self._sync_company_hint()

    def _destroy_all_toplevels(self) -> None:
        self._settings_win = None
        for w in list(self.root.winfo_children()):
            try:
                if w.winfo_class() == "Toplevel":
                    w.destroy()
            except tk.TclError:
                pass

    def _quit_app(self) -> None:
        if self._exiting:
            return
        if not messagebox.askokcancel("退出", "关闭招聘防骗并结束程序？"):
            return
        self._exiting = True
        if sys.platform == "win32":
            try:
                ctypes.windll.user32.UnregisterHotKey(self.root.winfo_id(), HOTKEY_ID)
            except Exception:
                pass
        self._destroy_all_toplevels()
        try:
            self.root.quit()
        except tk.TclError:
            pass
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def _collapse(self) -> None:
        if self.expanded:
            self._show_ball()

    def _toggle(self) -> None:
        if self.expanded:
            self._collapse()
        else:
            self._expand()
            self.root.lift()

    def _on_escape(self, _event=None) -> None:
        if self._selecting:
            return
        if self.expanded:
            text = self.input_box.get("1.0", "end").strip()
            if text and text != "识别中，请稍候…":
                self.input_box.delete("1.0", "end")
                self._set_status("已清空 · Esc 再次收起")
                return
            self._collapse()

    def _start_drag(self, event: tk.Event) -> None:
        self._moved = False
        self._drag = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag:
            self._moved = True
            x = event.x_root - self._drag[0]
            y = event.y_root - self._drag[1]
            w = EXPAND_W if self.expanded else BALL
            h = EXPAND_H if self.expanded else BALL
            self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _end_drag(self, event: tk.Event) -> None:
        if not self._moved and not self.expanded:
            self._expand()
        self._drag = None
        self._persist_ui_position()

    def _start_snip(self) -> None:
        if self._selecting:
            return
        self._selecting = True
        self.root.withdraw()
        self.root.update()
        RegionSelector(
            self.root,
            on_done=self._on_region_done,
            on_cancel=self._on_region_cancel,
        )

    def _on_region_cancel(self) -> None:
        self._selecting = False
        self.root.deiconify()
        self._show_ball()

    def _on_region_done(self, bbox: tuple[int, int, int, int]) -> None:
        self._selecting = False
        self.root.deiconify()
        self._expand()
        from app.ocr import get_ocr_status

        st = get_ocr_status()
        self._set_status(f"识别中（引擎: {st['preferred']}）…")
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", "识别中，请稍候…\n首次加载模型可能需 30～60 秒")
        threading.Thread(target=self._ocr_worker, args=(bbox,), daemon=True).start()

    def _ocr_worker(self, bbox: tuple[int, int, int, int]) -> None:
        err_msg: str | None = None
        result: tuple[str, str] | None = None
        try:
            img = grab_bbox(bbox)
            result = image_to_text(img)
        except Exception as exc:
            err_msg = str(exc)

        def finish() -> None:
            if err_msg:
                self._ocr_failed(err_msg)
            elif result:
                text, engine = result
                if not text.strip():
                    self._ocr_failed("未识别到文字，请框选更大、更清晰区域，或使用「粘贴检测」")
                else:
                    self._apply_ocr(text, engine)

        self.root.after(0, finish)

    def _apply_ocr(self, text: str, engine: str) -> None:
        min_chars = int(get_settings().get("ocr_min_chars") or 12)
        if len(text.strip()) < min_chars:
            self._ocr_failed(
                f"识别仅 {len(text.strip())} 字，可能不完整。\n"
                "建议框选更大区域，或点「粘贴检测」直接粘贴文字。"
            )
            if text.strip():
                self.input_box.delete("1.0", "end")
                self.input_box.insert("1.0", text)
            return
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", text)
        self._set_status(f"已识别（{engine}，{len(text)} 字）")
        self._analyze()

    def _ocr_failed(self, msg: str) -> None:
        self.input_box.delete("1.0", "end")
        self._apply_score_ui("失败")
        self.headline_label.configure(text="识别失败，建议改用粘贴")
        for i, al in enumerate(self.action_labels):
            al.configure(text=f"{i + 1}. 复制文字后点「粘贴检测」" if i == 0 else "")
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", msg)
        self.result_box.configure(state="disabled")
        self._set_status("识别失败 · 可点「粘贴检测」重试")
        if messagebox.askyesno("识别失败", f"{msg}\n\n是否立即粘贴剪贴板内容？"):
            self._paste_and_analyze()

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    def _paste_and_analyze(self) -> None:
        self._expand()
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showinfo("提示", "剪贴板为空")
            return
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", text)
        self._set_status("来自剪贴板")
        self._analyze()

    def _company_name(self) -> str:
        raw = self.company_input.get().strip()
        if raw:
            return normalize_company_name(raw)
        names = extract_company_names(self.input_box.get("1.0", "end"))
        return names[0] if names else ""

    def _open_platform(self, platform: str) -> None:
        name = self._company_name()
        if not name:
            messagebox.showinfo("提示", "未识别到公司名，请手动输入公司全称")
            return
        self.company_input.delete(0, "end")
        self.company_input.insert(0, name)
        try:
            url = open_platform(name, platform)
            labels = {"tianyancha": "天眼查", "qcc": "企查查", "aiqicha": "爱企查"}
            self._set_status(f"已打开{labels.get(platform, '')}：{name[:20]}")
        except Exception as exc:
            messagebox.showerror("打开失败", str(exc))

    def _open_both_platforms(self) -> None:
        name = self._company_name()
        if not name:
            messagebox.showinfo("提示", "未识别到公司名，请手动输入公司全称")
            return
        self.company_input.delete(0, "end")
        self.company_input.insert(0, name)
        try:
            open_platform(name, "tianyancha")
            open_platform(name, "qcc")
            self._set_status(f"已双开天眼查+企查查：{name[:18]}")
        except Exception as exc:
            messagebox.showerror("打开失败", str(exc))

    def _sync_company_hint(self) -> None:
        name = self.company_input.get().strip()
        if len(name) >= 2:
            self._set_status(f"可点「双开查询」核实：{name[:16]}")

    def _fill_company_from_text(self, text: str) -> None:
        name = best_company_name(text)
        if name:
            self.company_input.delete(0, "end")
            self.company_input.insert(0, normalize_company_name(name))
            self._set_status(f"识别到公司：{name}")
            return
        cur = self.company_input.get().strip()
        if cur and not is_plausible_company_name(cur):
            self.company_input.delete(0, "end")
        self._set_status("未识别到公司名，请手动填写工商全称")

    def _default_ai_provider(self) -> str:
        cfg = load_ai_config()
        p = (cfg.get("provider") or "").strip().lower()
        if p == "deepseek" and deepseek_ready():
            return "deepseek"
        if p == "gemini" and gemini_ready():
            return "gemini"
        if deepseek_ready():
            return "deepseek"
        if gemini_ready():
            return "gemini"
        return "none"

    def _current_ai_provider(self) -> str:
        return self.ai_provider.get().strip().lower()

    def _ai_label(self, provider: str) -> str:
        if provider == "deepseek":
            return "DeepSeek"
        if provider == "gemini":
            return "Gemini"
        return "AI"

    def _render_analysis(self, data: dict, text: str) -> None:
        self._last_result = data
        self._last_text = text
        level = data.get("risk_level", "低危")
        ai_info = data.get("ai") or {}
        display = data.get("risk_level_display") or self._risk_display(level)
        self._apply_score_ui(level, display)

        ctype = data.get("content_type_label") or "自动识别"
        self.type_badge.configure(text=ctype)

        headline = data.get("headline") or ""
        self.headline_label.configure(text=headline, font=(FONT, 10, "bold"))
        actions = data.get("actions") or []
        for i, al in enumerate(self.action_labels):
            if i < len(actions):
                al.configure(text=f"{i + 1}. {actions[i]}")
            else:
                al.configure(text="")

        decision = data.get("ai_decision") or ""
        ai = ai_info
        if ai.get("ok"):
            self.ai_decision_label.configure(text=f"✓ 已调用 {self._ai_label(ai.get('provider') or '')}", fg=LOW)
        elif ai.get("skipped") and ai.get("skip_reason"):
            self.ai_decision_label.configure(text=ai["skip_reason"], fg=MUTED)
        elif decision.startswith("skipped:"):
            self.ai_decision_label.configure(text=decision[8:], fg=MUTED)
        else:
            self.ai_decision_label.configure(text="AI 未启用", fg=MUTED)

        lines: list[str] = []
        breakdown_txt = data.get("score_breakdown_text")
        if breakdown_txt:
            lines.append(breakdown_txt)
            lines.append("")

        biz_warns = data.get("biz_warnings") or []
        if biz_warns:
            lines.append("【工商/经营信号】")
            lines.extend(f"  · {w}" for w in biz_warns)
            lines.append("")

        ai = ai_info
        plabel = self._ai_label(ai.get("provider") or "")
        if ai.get("used"):
            if ai.get("ok"):
                lines.append(f"【{plabel}】")
                if ai.get("summary"):
                    lines.append(f"  {ai['summary']}")
                for t in ai.get("scam_types") or []:
                    lines.append(f"  · 类型：{t}")
                for f in ai.get("red_flags") or []:
                    lines.append(f"  · {f}")
                if ai.get("model"):
                    lines.append(f"  （模型 {ai['model']}）")
            elif ai.get("skipped") and ai.get("skip_reason"):
                lines.append(f"【{plabel}】{ai['skip_reason']}")
            elif ai.get("error"):
                lines.append(f"【{plabel}】未成功：{ai['error']}")
            lines.append("")

        if data.get("url_warnings"):
            lines.append("【链接】")
            lines.extend(f"  · {w}" for w in data["url_warnings"])
        matches = data.get("matches") or []
        if matches:
            lines.append("【话术命中】")
            for m in matches:
                w = m.get("weight", 0)
                lines.append(f"  · {m.get('category_name', '')} (+{w})")
                for h in (m.get("hits") or [])[:4]:
                    lines.append(f"      {h}")
        else:
            lines.append("【话术命中】无明显风险规则")
        lines.append("")
        lines.append("【建议】")
        lines.extend(f"  · {s}" for s in data.get("suggestions") or [])

        self._fill_company_from_text(text)
        names = extract_company_names(text)

        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", "\n".join(lines))
        if names or self.company_input.get().strip():
            self.result_box.insert(
                "end",
                "\n\n【人工查企业】输入框下方点「双开查询」\n"
                "  重点看：实缴资本、最新年报参保人数\n",
            )
        self.result_box.configure(state="disabled")
        self._refresh_history()

    def _analyze(self) -> None:
        text = self.input_box.get("1.0", "end").strip()
        if not text or text == "识别中，请稍候…" or self._analyzing:
            return

        provider = self._current_ai_provider()
        use_ai = provider != "none" and is_provider_configured(provider)
        self._show_progress(True)
        if use_ai:
            self._analyzing = True
            plabel = self._ai_label(provider)
            self._set_status(f"规则检测中，{plabel} 分析需几秒…")
            threading.Thread(
                target=self._analyze_async,
                args=(text, provider),
                daemon=True,
            ).start()
            return

        try:
            data = analyze_full(text, "auto", use_ai=False, provider="none")
            self._render_analysis(data, text)
            self._set_status("检测完成")
        finally:
            self._show_progress(False)

    def _analyze_async(self, text: str, provider: str) -> None:
        try:
            data = analyze_full(
                text, "auto", use_ai=True, provider=provider
            )
        except Exception as e:
            data = analyze_full(text, "auto", use_ai=False, provider="none")
            data.setdefault("ai", {})["error"] = str(e)

        def finish() -> None:
            self._analyzing = False
            self._show_progress(False)
            self._render_analysis(data, text)
            plabel = self._ai_label(provider)
            ok = (data.get("ai") or {}).get("ok")
            self._set_status(f"检测完成（含 {plabel}）" if ok else "检测完成")

        self.root.after(0, finish)

    def _copy_checklist(self) -> None:
        text = self.input_box.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("提示", "请先检测或粘贴内容")
            return
        body = build_verification_checklist(text, self._last_result)
        self.root.clipboard_clear()
        self.root.clipboard_append(body)
        self._set_status("核查清单已复制到剪贴板")

    def _feedback_dialog(self) -> None:
        text = self.input_box.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("提示", "请先完成一次检测")
            return
        win = tk.Toplevel(self.root)
        win.title("误报反馈")
        win.configure(bg=PANEL)
        win.geometry("340x200")
        tk.Label(
            win,
            text="说明（可选）：为何判错？",
            font=(FONT, 9),
            fg=MUTED,
            bg=PANEL,
        ).pack(anchor="w", padx=12, pady=(12, 4))
        comment = tk.Text(win, height=4, font=(FONT, 9), bg=CARD, fg=TEXT, relief="flat")
        comment.pack(fill="x", padx=12)
        var = tk.StringVar(value="false_positive")

        def save() -> None:
            result = self._last_result or analyze_full(
                text, "auto", use_ai=False, provider="none", save_history=False
            )
            append_feedback(
                text,
                result,
                label=var.get(),
                comment=comment.get("1.0", "end").strip(),
            )
            win.destroy()
            self._set_status("感谢反馈，已写入 data/feedback.jsonl")

        row = tk.Frame(win, bg=PANEL)
        row.pack(fill="x", padx=12, pady=8)
        for val, lab in (
            ("false_positive", "误报偏高"),
            ("false_negative", "漏报偏低"),
            ("other", "其他"),
        ):
            tk.Radiobutton(
                row,
                text=lab,
                variable=var,
                value=val,
                bg=PANEL,
                fg=TEXT,
                selectcolor=ACCENT,
                activebackground=PANEL,
                font=(FONT, 8),
            ).pack(side="left", padx=(0, 8))
        tk.Button(
            win,
            text="提交",
            command=save,
            bg=ACCENT,
            fg="white",
            relief="flat",
            font=(FONT, 9),
            cursor="hand2",
        ).pack(pady=(0, 12))

    def _open_settings(self) -> None:
        if self._settings_win is not None:
            try:
                if self._settings_win.winfo_exists():
                    self._settings_win.deiconify()
                    self._settings_win.lift()
                    self._settings_win.focus_force()
                    return
            except tk.TclError:
                pass
            self._settings_win = None

        s = get_settings()
        win = tk.Toplevel(self.root)
        self._settings_win = win
        win.title("设置")
        win.configure(bg=PANEL)
        win.geometry("360x420")
        win.transient(self.root)

        def _clear_settings_ref() -> None:
            if self._settings_win is win:
                self._settings_win = None

        def _close_settings() -> None:
            _clear_settings_ref()
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _close_settings)
        body = tk.Frame(win, bg=PANEL)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        strict_var = tk.BooleanVar(value=bool(s.get("strict_mode", True)))
        tk.Checkbutton(
            body,
            text="严格筛查模式",
            variable=strict_var,
            bg=PANEL,
            fg=TEXT,
            selectcolor=ACCENT,
            activebackground=PANEL,
            font=(FONT, 9),
        ).pack(anchor="w")

        tk.Label(body, text="AI 策略（严格模式下）", font=(FONT, 8), fg=MUTED, bg=PANEL).pack(
            anchor="w", pady=(10, 2)
        )
        ai_trig = tk.StringVar(value=str(s.get("strict_ai_trigger") or "smart"))
        ttk.Combobox(
            body,
            textvariable=ai_trig,
            values=("smart", "always", "borderline", "high_risk_only"),
            state="readonly",
            width=28,
        ).pack(anchor="w")

        tk.Label(body, text="OCR 引擎", font=(FONT, 8), fg=MUTED, bg=PANEL).pack(
            anchor="w", pady=(10, 2)
        )
        ocr_var = tk.StringVar(value=str(s.get("ocr_engine") or "fast"))
        ttk.Combobox(
            body,
            textvariable=ocr_var,
            values=("fast", "auto", "paddle", "rapid", "windows"),
            state="readonly",
            width=28,
        ).pack(anchor="w")

        hist_var = tk.BooleanVar(value=bool(s.get("save_history", True)))
        tk.Checkbutton(
            body,
            text="保存检测历史",
            variable=hist_var,
            bg=PANEL,
            fg=TEXT,
            selectcolor=ACCENT,
            activebackground=PANEL,
            font=(FONT, 9),
        ).pack(anchor="w", pady=(8, 0))

        ocr_fix_var = tk.BooleanVar(value=bool(s.get("ocr_post_fix", True)))
        tk.Checkbutton(
            body,
            text="OCR 后自动纠错",
            variable=ocr_fix_var,
            bg=PANEL,
            fg=TEXT,
            selectcolor=ACCENT,
            activebackground=PANEL,
            font=(FONT, 9),
        ).pack(anchor="w")

        tk.Label(body, text="平台话术包", font=(FONT, 8), fg=MUTED, bg=PANEL).pack(
            anchor="w", pady=(10, 2)
        )
        pack_frame = tk.Frame(body, bg=PANEL)
        pack_frame.pack(anchor="w")
        enabled = set(s.get("enabled_platform_packs") or ["boss", "zhilian", "wechat"])
        pack_vars: dict[str, tk.BooleanVar] = {}
        for pid, lab in (("boss", "BOSS"), ("zhilian", "智联"), ("wechat", "微信私聊")):
            v = tk.BooleanVar(value=pid in enabled)
            pack_vars[pid] = v
            tk.Checkbutton(
                pack_frame,
                text=lab,
                variable=v,
                bg=PANEL,
                fg=TEXT,
                selectcolor=ACCENT,
                activebackground=PANEL,
                font=(FONT, 8),
            ).pack(anchor="w")

        def apply() -> None:
            packs = [pid for pid, v in pack_vars.items() if v.get()]
            save_settings_patch(
                {
                    "strict_mode": strict_var.get(),
                    "strict_ai_trigger": ai_trig.get(),
                    "ocr_engine": ocr_var.get(),
                    "save_history": hist_var.get(),
                    "ocr_post_fix": ocr_fix_var.get(),
                    "enabled_platform_packs": packs or ["boss"],
                }
            )
            reload_patterns()
            _clear_settings_ref()
            win.destroy()
            self._set_status("设置已保存，规则已重载")

        tk.Button(
            body,
            text="保存",
            command=apply,
            bg=ACCENT,
            fg="white",
            relief="flat",
            font=(FONT, 9),
            cursor="hand2",
        ).pack(pady=(16, 0))

    def _reload_patterns_menu(self) -> None:
        info = reload_patterns()
        self._set_status(
            f"规则已重载 v{info.get('version')} · 平台包 {info.get('packs')}"
        )

    def _export_history_clip(self) -> None:
        md = export_history_markdown(15)
        self.root.clipboard_clear()
        self.root.clipboard_append(md)
        self._set_status("历史 Markdown 已复制")

    def _context_menu(self, event: tk.Event) -> None:
        menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=CARD,
            fg=TEXT,
            activebackground=ACCENT,
            activeforeground="white",
            bd=0,
            relief="flat",
        )
        menu.add_command(label="框选识别", command=self._start_snip)
        menu.add_command(label="粘贴检测", command=self._paste_and_analyze)
        if self._company_name():
            menu.add_separator()
            menu.add_command(label="双开天眼查+企查查", command=self._open_both_platforms)
            menu.add_command(label="打开天眼查", command=lambda: self._open_platform("tianyancha"))
            menu.add_command(label="打开企查查", command=lambda: self._open_platform("qcc"))
        menu.add_separator()
        menu.add_command(label="设置…", command=self._open_settings)
        menu.add_command(label="重载规则", command=self._reload_patterns_menu)
        menu.add_command(label="导出历史(Markdown)", command=self._export_history_clip)
        if self._last_result:
            menu.add_command(label="复制核查清单", command=self._copy_checklist)
            menu.add_command(label="误报反馈…", command=self._feedback_dialog)
        menu.add_separator()
        menu.add_command(label="收起", command=self._collapse)
        menu.add_command(label="退出", command=self._quit_app)
        menu.tk_popup(event.x_root, event.y_root)

    def _register_hotkey(self) -> None:
        if sys.platform != "win32":
            return
        hwnd = self.root.winfo_id()
        ctypes.windll.user32.RegisterHotKey(hwnd, HOTKEY_ID, 0x0001 | 0x0004, 0x4A)

    def _poll_hotkey(self) -> None:
        if self._exiting:
            return
        if sys.platform == "win32":
            try:
                msg = wintypes.MSG()
                hwnd = self.root.winfo_id()
                while ctypes.windll.user32.PeekMessageW(
                    ctypes.byref(msg), hwnd, 0x0312, 0x0312, 1
                ):
                    if msg.message == 0x0312 and msg.wParam == HOTKEY_ID:
                        self._toggle()
            except Exception:
                pass
        self.root.after(80, self._poll_hotkey)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    _enable_dpi_awareness()
    FloatGuard().run()


if __name__ == "__main__":
    main()
