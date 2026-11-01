# -*- coding: utf-8 -*-
"""Trực quan hóa quá trình mã hóa / giải mã Tiny A5/1 trên cửa sổ Tkinter.

  - Khóa K (23 bit) chia cho X (6 bit), Y (8 bit), Z (9 bit).
  - Mỗi bit đầu vào đi qua 5 pha:
        1. m = maj(X[1], Y[3], Z[3])
        2. quay X nếu X[1] == m
        3. quay Y nếu Y[3] == m
        4. quay Z nếu Z[3] == m
        5. s = X[5] ⊕ Y[7] ⊕ Z[8], rồi XOR với bit đầu vào
  - "Quay" một thanh ghi: tính t từ các tap (trước khi dịch), dịch phải mọi bit
    một vị trí, bit cuối bị đẩy ra ngoài, chèn t vào vị trí 0. Bước này được
    làm hoạt ảnh trên Canvas: tô sáng tap -> gom về ⊕ -> các ô trượt sang phải
    -> bit cuối bị loại -> bit t rơi vào ô 0.

Cách dùng từ giao diện chính::

    from .tiny_visualizer import open_visualizer
    open_visualizer(root, key_bits, data_bits, decrypt=False)

Cửa sổ dùng lại các style của ``gui.py`` (Card.TFrame, Page.TFrame,
Heading.TLabel, Primary.TButton, Outline.TButton)
"""

from __future__ import annotations

import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import font as tkfont
from tkinter import ttk

# ======================================================================
# 1. Logic mô phỏng 
# ======================================================================
KEY_BITS = 23
REGISTERS = {
    "X": {"length": 6, "clock": 1, "taps": (2, 4, 5), "out": 5},
    "Y": {"length": 8, "clock": 3, "taps": (6, 7), "out": 7},
    "Z": {"length": 9, "clock": 3, "taps": (2, 7, 8), "out": 8},
}
NAMES = ("X", "Y", "Z")
PHASES = 5            # số pha cho mỗi bit đầu vào
LETTERS = "ABCDEFGH"  # A=000 ... H=111


def majority(a: int, b: int, c: int) -> int:
    return 1 if a + b + c >= 2 else 0


def letters_to_bits(text: str) -> str:
    """Chữ cái A–H -> 3 bit mỗi chữ (A=000 ... H=111)."""
    bits = []
    for ch in "".join(text.split()).upper():
        if ch not in LETTERS:
            raise ValueError(f"Ký tự '{ch}' nằm ngoài A–H.")
        bits.append(format(LETTERS.index(ch), "03b"))
    return "".join(bits)


def bits_to_letters(bits: str) -> str:
    """Chuỗi bit -> chữ cái, chỉ lấy các nhóm đủ 3 bit."""
    return "".join(LETTERS[int(bits[i:i + 3], 2)] for i in range(0, len(bits) - len(bits) % 3, 3))


@dataclass
class BitStep:
    index: int
    input_bit: int
    before: dict       # trạng thái 3 thanh ghi trước khi quay
    after: dict        # trạng thái sau khi quay
    clock_bits: dict   # bit điều khiển lấy trước khi quay
    m: int
    clocks: dict       # thanh ghi nào được quay
    tap_values: dict   # giá trị các tap (lấy từ trạng thái trước)
    t: dict            # bit phản hồi t = XOR các tap
    dropped: dict      # bit bị đẩy ra (None nếu không quay)
    out_bits: dict     # bit Out của mỗi thanh ghi SAU khi quay
    keystream: int
    output: int


@dataclass
class Simulation:
    key: str
    data: str
    decrypt: bool
    initial: dict
    initial_tap_values: dict
    initial_t: dict
    initial_out: dict
    initial_s: int
    steps: list
    keystream: str
    result: str


def _taps(name: str, bits: list) -> tuple:
    return tuple(bits[i] for i in REGISTERS[name]["taps"])


def build_simulation(key: str, data: str, decrypt: bool = False) -> Simulation:
    if len(key) != KEY_BITS or set(key) - {"0", "1"}:
        raise ValueError(f"Khóa Tiny A5/1 phải gồm đúng {KEY_BITS} bit 0/1.")
    if not data or set(data) - {"0", "1"}:
        raise ValueError("Dữ liệu đầu vào phải là chuỗi bit 0/1, không được rỗng.")

    regs, pos = {}, 0
    for name in NAMES:
        length = REGISTERS[name]["length"]
        regs[name] = [int(c) for c in key[pos:pos + length]]
        pos += length

    initial = {n: list(b) for n, b in regs.items()}
    initial_tap_values = {n: _taps(n, regs[n]) for n in NAMES}
    initial_t = {n: sum(initial_tap_values[n]) % 2 for n in NAMES}
    initial_out = {n: regs[n][REGISTERS[n]["out"]] for n in NAMES}
    initial_s = sum(initial_out.values()) % 2

    steps, keystream, result = [], [], []
    for i, ch in enumerate(data):
        p = int(ch)
        before = {n: list(b) for n, b in regs.items()}
        clock_bits = {n: before[n][REGISTERS[n]["clock"]] for n in NAMES}
        m = majority(*(clock_bits[n] for n in NAMES))
        clocks = {n: clock_bits[n] == m for n in NAMES}
        tap_values = {n: _taps(n, before[n]) for n in NAMES}
        t = {n: sum(tap_values[n]) % 2 for n in NAMES}

        dropped = {}
        for n in NAMES:
            if clocks[n]:
                dropped[n] = before[n][-1]
                regs[n] = [t[n]] + before[n][:-1]      # dịch phải, chèn t vào vị trí 0
            else:
                dropped[n] = None
        after = {n: list(b) for n, b in regs.items()}
        out_bits = {n: after[n][REGISTERS[n]["out"]] for n in NAMES}
        s = sum(out_bits.values()) % 2
        o = p ^ s
        keystream.append(str(s))
        result.append(str(o))
        steps.append(BitStep(i, p, before, after, clock_bits, m, clocks, tap_values,
                             t, dropped, out_bits, s, o))

    return Simulation(key, data, decrypt, initial, initial_tap_values, initial_t,
                      initial_out, initial_s, steps, "".join(keystream), "".join(result))


# ======================================================================
# 2. Bảng màu & hằng số vẽ
# ======================================================================
PAGE = "#f1f3f7"
CARD = "#ffffff"
BORDER = "#e0e4ea"
TEXT = "#1b2230"
MUTED = "#6f7887"
PRIMARY = "#1a7bff"
PRIMARY_SOFT = "#e8f1ff"
SEG_BG = "#eef1f6"

CLOCK, CLOCK_TINT, CLOCK_DARK = "#d97706", "#fff3d6", "#b45309"
TAP, TAP_TINT, TAP_FAINT, TAP_DARK = "#7c3aed", "#f1eafe", "#cfc3ee", "#6d28d9"
OUT, OUT_TINT, OUT_DARK = "#059669", "#dcf5e9", "#047857"
DROP, DROP_TINT, DROP_DARK = "#dc2626", "#fde8e8", "#b91c1c"

CANVAS_W, CANVAS_H = 590, 112
CELL_W, CELL_H = 42, 38
PITCH = 50                 # khoảng cách giữa hai ô liên tiếp
X0 = 52                    # lề trái tới ô 0
Y_BUS, Y_CELL = 18, 42
DROP_DX = PITCH + 8        # bit bị loại trượt thêm đoạn này ra khỏi ô cuối

DELAYS = (3000, 2400, 1900, 1500, 1200, 900, 650, 450)   # ms mỗi pha, theo mức tốc độ 1..8


def _pick_font(root: tk.Misc) -> str:
    available = set(tkfont.families(root))
    for name in ("Inter", "Be Vietnam Pro", "Poppins", "Segoe UI"):
        if name in available:
            return name
    return "TkDefaultFont"


def _rgb(color: str) -> tuple:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def mix(a: str, b: str, t: float) -> str:
    """Pha màu a -> b theo t (0..1)."""
    ra, rb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def ease_in_out(q: float) -> float:
    return q * q * (3 - 2 * q)


def ease_out_back(q: float) -> float:
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (q - 1) ** 3 + c1 * (q - 1) ** 2


def slot_x(i: int) -> float:
    return X0 + i * PITCH


# ======================================================================
# 3. Canvas vẽ một thanh ghi
# ======================================================================
class RegisterCanvas(tk.Canvas):
    """Vẽ một thanh ghi: các ô, sơ đồ phản hồi (tap -> ⊕ -> ô 0) và hoạt ảnh dịch phải."""

    def __init__(self, parent, name: str, family: str):
        super().__init__(parent, width=CANVAS_W, height=CANVAS_H, background=CARD,
                         highlightthickness=0, bd=0)
        self.name = name
        self.spec = REGISTERS[name]
        self.n = self.spec["length"]
        self.family = family
        self.mono = ("Consolas", 14, "bold")

    # ---- tiện ích vẽ --------------------------------------------------
    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.create_polygon(pts, smooth=True, **kw)

    def _role(self, i: int):
        if i == self.spec["clock"]:
            return "clock"
        if i == self.spec["out"]:
            return "out"
        if i in self.spec["taps"]:
            return "tap"
        return None

    # ---- các lớp nền ---------------------------------------------------
    def _draw_slots(self, highlight_out: bool) -> None:
        styles = {"clock": (CLOCK_TINT, CLOCK, 2), "out": (OUT_TINT, OUT, 2),
                  "tap": (TAP_TINT, TAP, 2), None: ("#f6f7fa", BORDER, 1)}
        colors = {"clock": CLOCK, "out": OUT, "tap": TAP}
        for i in range(self.n):
            x = slot_x(i)
            role = self._role(i)
            fill, outline, width = styles[role]
            if highlight_out and role == "out":
                fill, width = mix(OUT_TINT, OUT, 0.35), 3
            self._round_rect(x, Y_CELL, x + CELL_W, Y_CELL + CELL_H, 8,
                             fill=fill, outline=outline, width=width)
            self.create_text(x + CELL_W / 2, Y_CELL + CELL_H + 11, text=str(i),
                             fill=MUTED, font=(self.family, 9))
            labels = []
            if i == self.spec["clock"]:
                labels.append("Clock")
            if i in self.spec["taps"]:
                labels.append("Tap")
            if i == self.spec["out"]:
                labels.append("Out")
            if labels:
                self.create_text(x + CELL_W / 2, Y_CELL + CELL_H + 25, text="·".join(labels),
                                 fill=colors[role], font=(self.family, 9, "bold"))
        # vùng "ra khỏi thanh ghi" bên phải ô cuối
        gx = slot_x(self.n - 1) + DROP_DX
        self.create_rectangle(gx, Y_CELL, gx + CELL_W, Y_CELL + CELL_H,
                              outline=mix(DROP, CARD, 0.55), dash=(4, 3))
        self.create_text(gx + CELL_W / 2, Y_CELL + CELL_H + 11, text="Xóa",
                         fill=mix(DROP, CARD, 0.35), font=(self.family, 9, "bold"))

    def _draw_bus(self, t, on: bool) -> None:
        taps = self.spec["taps"]
        color = TAP if on else TAP_FAINT
        width = 2.5 if on else 1.5
        cx = lambda i: slot_x(i) + CELL_W / 2
        x0, xr = cx(0), cx(max(taps))
        self.create_line(x0, Y_BUS, xr, Y_BUS, fill=color, width=width)
        for i in taps:
            self.create_line(cx(i), Y_BUS, cx(i), Y_CELL, fill=color, width=width)
            self.create_oval(cx(i) - 3, Y_BUS - 3, cx(i) + 3, Y_BUS + 3, fill=color, outline=color)
        self.create_line(x0, Y_BUS + 12, x0, Y_CELL, fill=color, width=width, arrow="last")
        self.create_oval(x0 - 12, Y_BUS - 12, x0 + 12, Y_BUS + 12,
                         fill=TAP_TINT if on else CARD, outline=color, width=2)
        self.create_text(x0, Y_BUS, text="⊕", fill=color, font=(self.family, 12, "bold"))
        if t is not None:
            self.create_text(x0 - 18, Y_BUS, text=f"t={t}", anchor="e",
                             fill=TAP_DARK if on else MUTED, font=(self.family, 11, "bold"))

    # ---- ô bit ---------------------------------------------------------
    def _sprite(self, x, y, value, *, ring=None, style="normal", alpha=1.0) -> None:
        fill, outline, width = CARD, "#cfd5df", 1
        text = PRIMARY if value else MUTED
        if ring == "clock":
            fill, outline, width, text = CLOCK_TINT, CLOCK, 2, CLOCK_DARK
        elif ring == "tap":
            fill, outline, width, text = TAP_TINT, TAP, 2, TAP_DARK
        elif ring == "out":
            fill, outline, width, text = OUT_TINT, OUT, 2, OUT_DARK
        if style == "new":
            fill, outline, width, text = CLOCK_TINT, CLOCK, 2, CLOCK_DARK
        elif style == "drop":
            fill, outline, width, text = DROP_TINT, DROP, 2, DROP_DARK
        if alpha < 1:
            fill, outline, text = (mix(CARD, c, alpha) for c in (fill, outline, text))
        pad = 4
        self._round_rect(x + pad, y + pad, x + CELL_W - pad, y + CELL_H - pad, 6,
                         fill=fill, outline=outline, width=width)
        self.create_text(x + CELL_W / 2, y + CELL_H / 2, text=str(value), fill=text, font=self.mono)

    # ---- API vẽ --------------------------------------------------------
    def paint(self, bits=None, *, t=None, bus=False, ring=None, dropped=None, motion=None) -> None:
        """Vẽ lại toàn bộ thanh ghi.

        bits    : trạng thái hiển thị (khi không có hoạt ảnh)
        t       : giá trị bit phản hồi hiện ra cạnh ⊕
        bus     : tô đậm sơ đồ phản hồi
        ring    : "clock" | "tap" | "out" - tô sáng các ô cùng vai trò
        dropped : bit vừa bị đẩy ra (hiện mờ trong vùng "Xóa")
        motion  : dict(before, after, t, p) - khung hình hoạt ảnh, p = 0..1
        """
        self.delete("all")
        self._draw_slots(highlight_out=(ring == "out"))
        self._draw_bus(t, bus)
        if motion is None:
            for i, b in enumerate(bits):
                role = None
                if ring == "clock" and i == self.spec["clock"]:
                    role = "clock"
                elif ring == "tap" and i in self.spec["taps"]:
                    role = "tap"
                elif ring == "out" and i == self.spec["out"]:
                    role = "out"
                self._sprite(slot_x(i), Y_CELL, b, ring=role)
            if dropped is not None:
                gx = slot_x(self.n - 1) + DROP_DX
                self.create_text(gx + CELL_W / 2, Y_CELL + CELL_H / 2, text=str(dropped),
                                 fill=mix(DROP, CARD, 0.45), font=self.mono)
            return
        self._paint_motion(motion)

    def _paint_motion(self, mo: dict) -> None:
        """Dòng thời gian của một lần quay (p: 0 -> 1):

        0.00-0.22  tô sáng các tap, bit t hiện ở ⊕
        0.22-0.75  mọi ô trượt phải một vị trí, ô cuối trượt ra và mờ dần
        0.60-1.00  bit t rơi từ trên xuống vào ô 0
        """
        before, p = mo["before"], mo["p"]
        n, taps = self.n, self.spec["taps"]
        shift_q = clamp((p - 0.22) / 0.53)
        e = ease_in_out(shift_q)
        drop_q = clamp((p - 0.60) / 0.40)
        ring_taps = shift_q == 0

        for i in range(n - 1):
            ring = "tap" if ring_taps and i in taps else None
            self._sprite(slot_x(i) + e * PITCH, Y_CELL, before[i], ring=ring)
        last = n - 1
        if shift_q == 0:
            self._sprite(slot_x(last), Y_CELL, before[last], ring="tap" if last in taps else None)
        else:
            self._sprite(slot_x(last) + e * DROP_DX, Y_CELL, before[last],
                         style="drop", alpha=max(0.12, 1 - 0.85 * e))
        if drop_q > 0:
            eo = ease_out_back(drop_q)
            self._sprite(slot_x(0), Y_CELL - (1 - eo) * 34, mo["t"], style="new",
                         alpha=min(1.0, drop_q * 2.5))


# ======================================================================
# 4. Cửa sổ trực quan hóa
# ======================================================================
def _card(parent, padding: int = 14):
    outer = tk.Frame(parent, background=CARD, highlightbackground=BORDER,
                     highlightcolor=BORDER, highlightthickness=2, bd=0)
    inner = ttk.Frame(outer, padding=padding, style="Card.TFrame")
    inner.pack(fill="both", expand=True)
    return outer, inner


class TinyA51Visualizer(tk.Toplevel):
    """Cửa sổ mô phỏng từng bước. ``pos`` chạy từ 0 (trạng thái ban đầu) tới 5 × số bit."""

    def __init__(self, master, sim: Simulation):
        super().__init__(master)
        self.sim = sim
        self.total = len(sim.steps) * PHASES
        self.pos = 0
        self.playing = False
        self._auto_job = None
        self._anim_job = None
        self._anim_name = None
        self.family = _pick_font(self)
        self.level = tk.DoubleVar(value=5)

        verb = "Giải mã" if sim.decrypt else "Mã hóa"
        self.title(f"Trực quan hóa Tiny A5/1 — {verb}")
        self.configure(background=PAGE)
        width = 1300
        height = min(800, max(620, self.winfo_screenheight() - 80))
        self.geometry(f"{width}x{height}+40+30")
        self.minsize(1120, 620)
        self.protocol("WM_DELETE_WINDOW", self.close)

        self._ensure_styles()
        self._build()
        self.bind("<Right>", lambda _e: self.on_next())
        self.bind("<Left>", lambda _e: self.on_back())
        self.bind("<p>", lambda _e: self.toggle_play())
        self._render()
        self.lift()

    # ------------------------------------------------------------------
    # Dựng giao diện
    # ------------------------------------------------------------------
    def _ensure_styles(self) -> None:
        s, f = ttk.Style(self), self.family
        s.configure("VizTitle.TLabel", background=PAGE, foreground=TEXT, font=(f, 20, "bold"))
        s.configure("VizSub.TLabel", background=PAGE, foreground=MUTED, font=(f, 11))
        s.configure("VizCard.TLabel", background=CARD, foreground=TEXT, font=(f, 12))
        s.configure("VizHead.TLabel", background=CARD, foreground=TEXT, font=(f, 14, "bold"))
        s.configure("VizProgress.TLabel", background=CARD, foreground=PRIMARY, font=(f, 13, "bold"))
        s.configure("Viz.Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT,
                    rowheight=28, font=(f, 11), borderwidth=0)
        s.configure("Viz.Treeview.Heading", font=(f, 10, "bold"), background=SEG_BG,
                    foreground=MUTED, relief="flat", padding=6)
        s.map("Viz.Treeview", background=[("selected", PRIMARY_SOFT)], foreground=[("selected", TEXT)])
        s.configure("Viz.Horizontal.TScale", background=CARD, troughcolor=PRIMARY_SOFT)

    def _make_text(self, parent, height: int) -> tk.Text:
        f = self.family
        t = tk.Text(parent, height=height, width=10, wrap="word", relief="flat", bd=0, highlightthickness=0,
                    background=CARD, foreground=TEXT, font=(f, 12), padx=2, pady=2,
                    cursor="arrow", state="disabled", spacing1=2, spacing3=2)
        t.tag_configure("h", font=(f, 13, "bold"), spacing3=6)
        t.tag_configure("b", font=(f, 12, "bold"))
        t.tag_configure("mono", font=("Consolas", 12), background="#f6f7fa", lmargin1=8, lmargin2=8)
        t.tag_configure("muted", foreground=MUTED)
        t.tag_configure("amber", foreground=CLOCK_DARK, font=(f, 12, "bold"))
        t.tag_configure("purple", foreground=TAP_DARK, font=(f, 12, "bold"))
        t.tag_configure("green", foreground=OUT_DARK, font=(f, 12, "bold"))
        t.tag_configure("red", foreground=DROP_DARK, font=(f, 12, "bold"))
        t.tag_configure("cur", background=CLOCK_TINT)
        return t

    def _build(self) -> None:
        f, sim = self.family, self.sim
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ---- Tiêu đề + thông tin đầu vào ---------------------------------
        header = ttk.Frame(self, style="Page.TFrame", padding=(24, 14, 24, 2))
        header.grid(row=0, column=0, sticky="ew")
        verb = "Giải mã" if sim.decrypt else "Mã hóa"
        kx, ky, kz = sim.key[:6], sim.key[6:14], sim.key[14:]
        label_in = "Bản mã C" if sim.decrypt else "Bản rõ P"
        ttk.Label(header, style="VizSub.TLabel", wraplength=1200, justify="left",
                  text=f"Tiny A5/1 · {verb}      Khóa K = {kx} | {ky} | {kz}  (X | Y | Z)"
                       f"      {label_in} = {sim.data}").pack(anchor="w")

        # ---- Thanh điều khiển ---------------------------------------------
        bar_outer, bar = _card(self, 12)
        bar_outer.grid(row=1, column=0, sticky="ew", padx=24, pady=(6, 0))
        bar.columnconfigure(5, weight=1)
        self.btn_first = ttk.Button(bar, text="Về đầu", width=0, style="Outline.TButton", command=self.on_first)
        self.btn_back = ttk.Button(bar, text="Lùi", width=0, style="Outline.TButton", command=self.on_back)
        self.btn_play = ttk.Button(bar, text="Chạy tự động", width=0, style="Primary.TButton", command=self.toggle_play)
        self.btn_next = ttk.Button(bar, text="Bước kế", width=0, style="Outline.TButton", command=self.on_next)
        self.btn_last = ttk.Button(bar, text="Đến cuối", width=0, style="Outline.TButton", command=self.on_last)
        for col, b in enumerate((self.btn_first, self.btn_back, self.btn_play, self.btn_next, self.btn_last)):
            b.grid(row=0, column=col, padx=(0, 8))
        self.progress_text = tk.StringVar()
        ttk.Label(bar, textvariable=self.progress_text, style="VizProgress.TLabel").grid(
            row=0, column=5, sticky="e", padx=(12, 20))
        speed = ttk.Frame(bar)
        speed.grid(row=0, column=6, sticky="e")
        self.speed_text = tk.StringVar()
        ttk.Label(speed, textvariable=self.speed_text, style="VizCard.TLabel").grid(row=0, column=0, padx=(0, 10))
        ttk.Scale(speed, from_=1, to=8, variable=self.level, length=140, style="Viz.Horizontal.TScale",
                  takefocus=False, command=lambda _v: self._update_speed_text()).grid(row=0, column=1)
        self._update_speed_text()

        # ---- Vùng chính -----------------------------------------------------
        main = ttk.Frame(self, style="Page.TFrame", padding=(24, 12, 24, 18))
        main.grid(row=2, column=0, sticky="nsew")
        main.columnconfigure(0, weight=0, minsize=CANVAS_W + 40)
        main.columnconfigure(1, weight=1, minsize=420)
        main.rowconfigure(0, weight=1)
        left = ttk.Frame(main, style="Page.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        left.columnconfigure(0, weight=1)
        right = ttk.Frame(main, style="Page.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=5)
        right.rowconfigure(2, weight=1)

        # Thanh 5 pha (bấm để nhảy tới pha đó của bit hiện tại)
        stepper = ttk.Frame(left, style="Page.TFrame")
        stepper.grid(row=0, column=0, sticky="ew")
        self.pills = []
        for k in range(PHASES):
            stepper.columnconfigure(k, weight=1, uniform="pill")
            pill = tk.Label(stepper, font=(f, 10, "bold"), cursor="hand2", pady=7,
                            highlightthickness=1, highlightbackground=BORDER, bd=0)
            pill.grid(row=0, column=k, sticky="ew", padx=(0 if k == 0 else 4, 0))
            pill.bind("<Button-1>", lambda _e, k=k: self.on_phase_click(k))
            self.pills.append(pill)

        # Ba thẻ thanh ghi
        self.cards = {}
        for row, name in enumerate(NAMES, start=1):
            spec = REGISTERS[name]
            outer, inner = _card(left, 8)
            outer.grid(row=row, column=0, sticky="ew", pady=(8, 0))
            inner.columnconfigure(1, weight=1)
            ttk.Label(inner, text=f"Thanh ghi {name}", style="VizHead.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(inner, text=f"{spec['length']} bit", style="VizCard.TLabel", foreground=MUTED).grid(
                row=0, column=0, sticky="w", padx=(125, 0))
            badge = tk.Label(inner, font=(f, 10, "bold"), padx=10, pady=2, bd=0)
            badge.grid(row=0, column=1, sticky="w", padx=(12, 0))
            tags = ttk.Frame(inner)
            tags.grid(row=0, column=2, sticky="e")
            for text, color in ((f"Clock {name}[{spec['clock']}]", CLOCK_DARK),
                                (f"Tap {list(spec['taps'])}", TAP_DARK),
                                (f"Out {name}[{spec['out']}]", OUT_DARK)):
                tk.Label(tags, text=text, fg=color, bg=CARD, font=(f, 10, "bold")).pack(side="left", padx=(10, 0))
            formula = tk.StringVar()
            tk.Label(inner, textvariable=formula, fg=TAP_DARK, bg=CARD, anchor="w",
                     font=("Consolas", 11)).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 0))
            canvas = RegisterCanvas(inner, name, f)
            canvas.grid(row=2, column=0, columnspan=3, sticky="w")
            self.cards[name] = {"outer": outer, "badge": badge, "formula": formula, "canvas": canvas}

        # Cột phải: giải thích / kết quả / nhật ký
        exp_outer, exp = _card(right, 12)
        exp_outer.grid(row=0, column=0, sticky="nsew")
        exp.columnconfigure(0, weight=1)
        exp.rowconfigure(1, weight=1)
        ttk.Label(exp, text="Giải thích bước hiện tại", style="VizHead.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w")
        self.explain = self._make_text(exp, 6)
        exp_scroll = ttk.Scrollbar(exp, orient="vertical", command=self.explain.yview)
        self.explain.configure(yscrollcommand=exp_scroll.set)
        self.explain.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        exp_scroll.grid(row=1, column=1, sticky="ns", pady=(6, 0))

        sum_outer, summ = _card(right, 12)
        sum_outer.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        summ.columnconfigure(0, weight=1)
        ttk.Label(summ, text="Kết quả tích lũy", style="VizHead.TLabel").grid(row=0, column=0, sticky="w")
        self.summary = self._make_text(summ, 5)
        self.summary.tag_configure("mono", background=CARD, lmargin1=0, lmargin2=0, font=("Consolas", 13))
        self.summary.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        log_outer, log = _card(right, 12)
        log_outer.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        log.columnconfigure(0, weight=1)
        log.rowconfigure(1, weight=1)
        ttk.Label(log, text="Nhật ký các bit (bấm để nhảy tới)", style="VizHead.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w")
        cols = ("bit", "in", "clk", "m", "rot", "s", "out")
        self.tree = ttk.Treeview(log, columns=cols, show="headings", height=3,
                                 selectmode="browse", style="Viz.Treeview")
        heads = (("bit", "Bit", 44), ("in", "Vào", 46), ("clk", "(X1,Y3,Z3)", 96),
                 ("m", "m", 34), ("rot", "Quay", 74), ("s", "s", 34), ("out", "Ra", 44))
        for key, text, w in heads:
            self.tree.heading(key, text=text)
            self.tree.column(key, width=w, anchor="center", stretch=(key == "rot"))
        for st in sim.steps:
            c = st.clock_bits
            self.tree.insert("", "end", iid=str(st.index), values=(
                st.index, st.input_bit, f"({c['X']}, {c['Y']}, {c['Z']})", st.m,
                ", ".join(n for n in NAMES if st.clocks[n]), st.keystream, st.output))
        scroll = ttk.Scrollbar(log, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        scroll.grid(row=1, column=1, sticky="ns", pady=(6, 0))
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    # ------------------------------------------------------------------
    # Điều hướng
    # ------------------------------------------------------------------
    def _decode(self):
        """pos -> (chỉ số bit, pha 0..4); (None, None) ở trạng thái ban đầu."""
        if self.pos == 0:
            return None, None
        return (self.pos - 1) // PHASES, (self.pos - 1) % PHASES

    def _delay(self) -> int:
        return DELAYS[int(round(self.level.get())) - 1]

    def _update_speed_text(self) -> None:
        self.speed_text.set(f"Tốc độ ×{int(round(self.level.get()))}")

    def _stop(self) -> None:
        self.playing = False
        if self._auto_job is not None:
            self.after_cancel(self._auto_job)
            self._auto_job = None
        self.btn_play.configure(text="Chạy tự động")

    def _cancel_anim(self) -> None:
        if self._anim_job is not None:
            self.after_cancel(self._anim_job)
            self._anim_job = None
        self._anim_name = None

    def go_to(self, pos: int) -> None:
        self._cancel_anim()
        self.pos = int(clamp(pos, 0, self.total))
        self._render()

    def step_forward(self) -> int:
        """Tiến một pha; trả về thời lượng hoạt ảnh (ms), 0 nếu không có."""
        if self.pos >= self.total:
            return 0
        self._cancel_anim()
        self.pos += 1
        bit, phase = self._decode()
        anim, duration = None, 0
        if phase in (1, 2, 3):
            name = NAMES[phase - 1]
            if self.sim.steps[bit].clocks[name]:
                anim, duration = name, int(min(1600, self._delay() * 0.8))
        self._render(anim=anim)
        if anim:
            self._start_anim(anim, duration)
        return duration

    def on_first(self) -> None:
        self._stop()
        self.go_to(0)

    def on_last(self) -> None:
        self._stop()
        self.go_to(self.total)

    def on_back(self) -> None:
        self._stop()
        self.go_to(self.pos - 1)

    def on_next(self) -> None:
        self._stop()
        self.step_forward()

    def on_phase_click(self, k: int) -> None:
        bit, _ = self._decode()
        if bit is None:
            return
        self._stop()
        self.go_to(1 + bit * PHASES + k)

    def on_tree_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        bit = int(sel[0])
        if bit == self._decode()[0]:
            return
        self._stop()
        self.go_to(1 + bit * PHASES)

    def toggle_play(self) -> None:
        if self.playing:
            self._stop()
            return
        if self.pos >= self.total:
            self.go_to(0)
        self.playing = True
        self.btn_play.configure(text="Tạm dừng")
        self._auto_tick()

    def _auto_tick(self) -> None:
        self._auto_job = None
        if not self.playing:
            return
        if self.pos >= self.total:
            self._stop()
            return
        self.step_forward()
        if self.pos >= self.total:
            self._stop()
            return
        self._auto_job = self.after(self._delay(), self._auto_tick)

    def close(self) -> None:
        self._stop()
        self._cancel_anim()
        self.destroy()

    # ------------------------------------------------------------------
    # Hoạt ảnh
    # ------------------------------------------------------------------
    def _start_anim(self, name: str, duration: int) -> None:
        bit, _ = self._decode()
        step = self.sim.steps[bit]
        canvas = self.cards[name]["canvas"]
        t0 = time.perf_counter()
        self._anim_name = name

        def frame() -> None:
            p = min(1.0, (time.perf_counter() - t0) * 1000 / max(1, duration))
            canvas.paint(t=step.t[name], bus=True,
                         motion={"before": step.before[name], "after": step.after[name],
                                 "t": step.t[name], "p": p})
            if p < 1.0:
                self._anim_job = self.after(15, frame)
            else:
                self._anim_job = None
                self._anim_name = None
                self._paint_register(name)

        frame()

    # ------------------------------------------------------------------
    # Vẽ lại giao diện theo pos
    # ------------------------------------------------------------------
    def _paint_register(self, name: str) -> None:
        bit, phase = self._decode()
        canvas = self.cards[name]["canvas"]
        if bit is None:
            canvas.paint(self.sim.initial[name], t=self.sim.initial_t[name])
            return
        step = self.sim.steps[bit]
        idx = NAMES.index(name)
        done = phase >= idx + 1
        bits = step.after[name] if done else step.before[name]
        active = phase == idx + 1 and step.clocks[name]
        ring = "clock" if phase == 0 else ("out" if phase == 4 else None)
        dropped = step.dropped[name] if done and step.clocks[name] else None
        canvas.paint(bits, t=step.t[name], bus=active, ring=ring, dropped=dropped)

    def _render(self, anim=None) -> None:
        bit, phase = self._decode()
        step = self.sim.steps[bit] if bit is not None else None
        n = len(self.sim.steps)

        # tiến trình
        if bit is None:
            self.progress_text.set("Trạng thái ban đầu")
        else:
            tail = " · Xong" if self.pos >= self.total else ""
            self.progress_text.set(f"Bit {bit}/{n - 1} · Pha {phase + 1}/{PHASES}{tail}")

        # 5 pha
        base = ["1  Tính m", "2  Quay X", "3  Quay Y", "4  Quay Z", "5  Sinh s & XOR"]
        for k, pill in enumerate(self.pills):
            text = base[k]
            if step is not None and 1 <= k <= 3 and not step.clocks[NAMES[k - 1]]:
                text = f"{k + 1}  {NAMES[k - 1]} dừng"
            if step is None or phase is None:
                bg, fg = CARD, MUTED
            elif k == phase:
                bg, fg = PRIMARY, "#ffffff"
            elif k < phase:
                bg, fg = PRIMARY_SOFT, PRIMARY
            else:
                bg, fg = CARD, MUTED
            pill.configure(text=text, background=bg, foreground=fg)

        # thanh ghi
        for idx, name in enumerate(NAMES):
            self._update_card(name, idx, step, phase)
            if name != anim:
                self._paint_register(name)

        self._write(self.explain, self._explain_segments(bit, phase))
        self._write(self.summary, self._summary_segments(bit, phase))
        self._sync_tree(bit)

        last = self.pos >= self.total
        self.btn_first.configure(state="disabled" if self.pos == 0 else "normal")
        self.btn_back.configure(state="disabled" if self.pos == 0 else "normal")
        self.btn_next.configure(state="disabled" if last else "normal")
        self.btn_last.configure(state="disabled" if last else "normal")

    def _update_card(self, name: str, idx: int, step, phase) -> None:
        spec, card = REGISTERS[name], self.cards[name]
        terms = " ⊕ ".join(f"{name}[{i}]" for i in spec["taps"])
        if step is None:
            vals = self.sim.initial_tap_values[name]
            t = self.sim.initial_t[name]
            card["badge"].configure(text="Chờ", background=SEG_BG, foreground=MUTED)
            note, border = "   (nếu quay)", BORDER
        else:
            vals, t = step.tap_values[name], step.t[name]
            c = spec["clock"]
            if step.clocks[name]:
                card["badge"].configure(text=f"Quay · {name}[{c}] = m", background=CLOCK_TINT,
                                        foreground=CLOCK_DARK)
                note = ""
            else:
                card["badge"].configure(text=f"Dừng · {name}[{c}] ≠ m", background=SEG_BG,
                                        foreground=MUTED)
                note = "   (đứng yên nên t không được chèn)"
            border = CLOCK if phase == idx + 1 else BORDER
        card["formula"].set(f"t = {terms} = {' ⊕ '.join(map(str, vals))} = {t}{note}")
        card["outer"].configure(highlightbackground=border, highlightcolor=border)

    def _sync_tree(self, bit) -> None:
        if bit is None:
            if self.tree.selection():
                self.tree.selection_remove(self.tree.selection())
            return
        iid = str(bit)
        if self.tree.selection() != (iid,):
            self.tree.selection_set(iid)
        self.tree.see(iid)

    # ------------------------------------------------------------------
    # Văn bản giải thích & kết quả
    # ------------------------------------------------------------------
    @staticmethod
    def _write(widget: tk.Text, segments) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        for text, tag in segments:
            widget.insert("end", text, tag) if tag else widget.insert("end", text)
        widget.configure(state="disabled")
        widget.yview_moveto(0)

    @staticmethod
    def _bits(bits) -> str:
        return "".join(map(str, bits))

    def _explain_segments(self, bit, phase):
        sim, seg = self.sim, []
        add = lambda text, tag=None: seg.append((text, tag))
        S = self._bits

        if bit is None:
            add("Trạng thái ban đầu\n", "h")
            add("Khóa K (23 bit) được chia lần lượt cho ba thanh ghi: X nhận 6 bit đầu, "
                "Y nhận 8 bit tiếp theo, Z nhận 9 bit cuối.\n")
            add(f"X = K[0..5]   = {S(sim.initial['X'])}\n"
                f"Y = K[6..13]  = {S(sim.initial['Y'])}\n"
                f"Z = K[14..22] = {S(sim.initial['Z'])}\n", "mono")
            add("\nMỗi bit đầu vào đi qua 5 pha: (1) tính m = maj(X[1], Y[3], Z[3]); "
                "(2–4) quay X, Y, Z nếu bit điều khiển bằng m; (5) lấy s = X[5] ⊕ Y[7] ⊕ Z[8] "
                "rồi XOR với bit đầu vào.\n")
            o = sim.initial_out
            add(f"\nTham khảo: trước khi quay, X[5] ⊕ Y[7] ⊕ Z[8] = {o['X']} ⊕ {o['Y']} ⊕ {o['Z']} "
                f"= {sim.initial_s}. Bit dùng để mã hóa bit đầu tiên được lấy sau lần quay thứ nhất.\n", "muted")
            add("\nNhấn «Bước kế» hoặc «Chạy tự động» để bắt đầu.", "b")
            return seg

        step = sim.steps[bit]
        cb, m = step.clock_bits, step.m
        a, b, c = cb["X"], cb["Y"], cb["Z"]

        if phase == 0:
            add(f"Bit {bit} · Pha 1/5: tính m\n", "h")
            add("Lấy bit điều khiển (Clock) của từng thanh ghi rồi tính bit đa số:\n")
            add(f"X[1] = {a}    Y[3] = {b}    Z[3] = {c}\n"
                f"m = maj({a}, {b}, {c}) = {m}\n", "mono")
            add("\nThanh ghi nào có bit điều khiển bằng m thì quay, các thanh ghi còn lại đứng yên:\n")
            for name in NAMES:
                ci = REGISTERS[name]["clock"]
                eq = "=" if step.clocks[name] else "≠"
                add(f"{name}[{ci}] = {cb[name]} {eq} {m}  →  ", "mono")
                if step.clocks[name]:
                    add("Quay\n", "amber")
                else:
                    add("Dừng\n", "muted")
            add("\nLuôn có ít nhất hai thanh ghi quay trong mỗi bit.", "muted")
            return seg

        if phase in (1, 2, 3):
            name = NAMES[phase - 1]
            spec = REGISTERS[name]
            ci, n_len = spec["clock"], spec["length"]
            if step.clocks[name]:
                terms = " ⊕ ".join(f"{name}[{i}]" for i in spec["taps"])
                vals = " ⊕ ".join(map(str, step.tap_values[name]))
                add(f"Bit {bit} · Pha {phase + 1}/5: quay {name}\n", "h")
                add(f"{name}[{ci}] = {cb[name]} bằng m = {m} nên {name} được quay. Việc quay gồm ba việc:\n")
                add("① Tính bit phản hồi t", "purple")
                add(" từ các tap, lấy trước khi dịch:\n")
                add(f"t = {terms} = {vals} = {step.t[name]}\n", "mono")
                add("② Dịch phải", "amber")
                add(f" một vị trí: mỗi bit {name}[j-1] chuyển sang {name}[j]. Bit cuối ")
                add(f"{name}[{n_len - 1}] = {step.dropped[name]}", "red")
                add(" bị đẩy ra ngoài và bị loại bỏ.\n")
                add("③ Chèn t", "amber")
                add(f" = {step.t[name]} vào vị trí {name}[0].\n")
                add(f"trước: {S(step.before[name])}\nsau:   {S(step.after[name])}\n", "mono")
            else:
                add(f"Bit {bit} · Pha {phase + 1}/5: {name} đứng yên\n", "h")
                add(f"{name}[{ci}] = {cb[name]} khác m = {m} nên {name} không quay: "
                    "không có phép dịch nào và trạng thái giữ nguyên.\n")
                add(f"{name} = {S(step.before[name])}\n", "mono")
                add(f"\n(Bit t = {step.t[name]} vẫn tính được nhưng không được chèn vào.)", "muted")
            return seg

        # phase == 4
        o = step.out_bits
        add(f"Bit {bit} · Pha 5/5: sinh bit khóa dòng và XOR\n", "h")
        add("Sau khi quay, bit khóa dòng s lấy từ bit cuối (Out) của ba thanh ghi:\n")
        add(f"s_{bit} = X[5] ⊕ Y[7] ⊕ Z[8]\n    = {o['X']} ⊕ {o['Y']} ⊕ {o['Z']} = {step.keystream}\n", "mono")
        if sim.decrypt:
            add("\nGiải mã: bản mã C ⊕ s = bản rõ P\n")
            add(f"C_{bit} ⊕ s_{bit} = {step.input_bit} ⊕ {step.keystream} = {step.output}\n", "mono")
            add(f"\nBit bản rõ P_{bit} = ")
            add(f"{step.output}\n", "green")
        else:
            add("\nMã hóa: bản rõ P ⊕ s = bản mã C\n")
            add(f"P_{bit} ⊕ s_{bit} = {step.input_bit} ⊕ {step.keystream} = {step.output}\n", "mono")
            add(f"\nBit bản mã C_{bit} = ")
            add(f"{step.output}\n", "green")
        return seg

    def _summary_segments(self, bit, phase):
        sim, seg = self.sim, []
        n = len(sim.steps)
        done = 0 if bit is None else bit + (1 if phase == PHASES - 1 else 0)
        in_label, out_label = ("Bản mã C", "Bản rõ P") if sim.decrypt else ("Bản rõ P", "Bản mã C")
        rows = ((in_label, sim.data),
                ("Dãy khóa S", sim.keystream[:done] + "·" * (n - done)),
                (out_label, sim.result[:done] + "·" * (n - done)))
        for label, text in rows:
            seg.append((f"{label:<11}", ("mono", "muted")))
            for i, ch in enumerate(text):
                if i and i % 3 == 0:
                    seg.append((" ", "mono"))
                seg.append((ch, ("mono", "cur") if bit is not None and i == bit else "mono"))
            seg.append(("\n", "mono"))
        if done == n:
            ok = "".join(str(int(a) ^ int(b)) for a, b in zip(sim.result, sim.keystream)) == sim.data
            seg.append((f"Kiểm tra đảo ngược: {'đúng ✓' if ok else 'sai ✗'}  "
                        f"({out_label[-1]} ⊕ S = {in_label[-1]})\n", "green" if ok else "red"))
            if n % 3 == 0:
                seg.append((f"Ký tự: {bits_to_letters(sim.data)} → {bits_to_letters(sim.result)}", "b"))
        return seg


def open_visualizer(master, key_bits: str, data_bits: str, decrypt: bool = False) -> TinyA51Visualizer:
    """Dựng mô phỏng và mở cửa sổ. Ném ValueError nếu khóa / dữ liệu không hợp lệ."""
    sim = build_simulation(key_bits, data_bits, decrypt)
    return TinyA51Visualizer(master, sim)