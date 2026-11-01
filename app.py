# -*- coding: utf-8 -*-
"""Giao diện Tkinter. Chỉ vẽ widget; mọi xử lý đi qua ``CipherController``.

Cửa sổ có hai tab:
  - "A5/1 đầy đủ": nhập bit nhị phân / nhập văn bản / tải tệp .txt
  - "Tiny A5/1":   nhập bit nhị phân / nhập ký tự

Bố cục mỗi tab (hai cột, các khối là thẻ trắng trên nền xám nhạt):

    ┌ Tùy chọn ─┐  ┌ Khóa ─────────────────────────┐
    │ Chức năng │  └───────────────────────────────┘
    │ Kiểu vào  │  ┌ Dữ liệu đầu vào ──────────────┐
    │ Số khung  │  │ [Mã hóa]  ━━ tiến trình ━━    │
    │ Định dạng │  └───────────────────────────────┘
    │ Ghi chú   │  ┌ Kết quả ─────  [Lưu] [Chép] ──┐
    └───────────┘  │ (khung lớn, nhiều dòng)       │
                   └───────────────────────────────┘
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
from tkinter.scrolledtext import ScrolledText

from service import ALGO_A51, ALGO_TINY
from .tiny_visualizer import letters_to_bits, open_visualizer
from .controller import (
    DECRYPT, ENCRYPT, MODE_BINARY, MODE_CHARS, MODE_FILE, MODE_TEXT,
    CipherController, OutputView,
)

OPERATIONS = {"Mã hóa": ENCRYPT, "Giải mã": DECRYPT}

# Nhãn ô nhập theo (kiểu nhập, chức năng)
INPUT_LABELS = {
    (MODE_BINARY, ENCRYPT): "Bản rõ (chuỗi bit 0/1)",
    (MODE_BINARY, DECRYPT): "Bản mã (chuỗi bit 0/1)",
    (MODE_TEXT, ENCRYPT): "Văn bản cần mã hóa",
    (MODE_TEXT, DECRYPT): "Bản mã dạng hex",
    (MODE_CHARS, ENCRYPT): "Chữ cái cần mã hóa (A đến H, không phân biệt hoa thường)",
    (MODE_CHARS, DECRYPT): "Bản mã (chuỗi bit 0/1, số bit chia hết cho 3)",
    (MODE_FILE, ENCRYPT): "Tệp văn bản .txt (UTF-8, tối đa 64 KiB)",
    (MODE_FILE, DECRYPT): "Tệp .txt chứa bản mã Base64 do chương trình tạo",
}

# ----------------------------------------------------------------------
# Bảng màu:
# ----------------------------------------------------------------------
PAGE = "#f1f3f7"          # nền cửa sổ
CARD = "#ffffff"          # nền thẻ / ô nhập
BORDER = "#e0e4ea"        # viền mảnh
TEXT = "#1b2230"          # chữ chính
MUTED = "#6f7887"         # chữ phụ
PRIMARY = "#1a7bff"       # xanh dương chủ đạo
PRIMARY_DARK = "#0f63d6"
PRIMARY_SOFT = "#e8f1ff"  # nền xanh nhạt
SEG_BG = "#eef1f6"        # nền nút chuyển (Mã hóa / Giải mã) khi chưa chọn
DISABLED_BG = "#f3f4f7"
DISABLED_FG = "#aab0bb"

# Cỡ chữ
FS_BODY = 12
FS_LABEL = 11
FS_HEADING = 14
FS_TITLE = 26
FS_SMALL = 10
FS_MONO = 13

# Kích thước các khung
INPUT_HEIGHT = 3          # số dòng của ô nhập văn bản
RESULT_HEIGHT = 14        # số dòng của ô kết quả
RESULT_MIN_SIZE = 260     # chiều cao tối thiểu (px) của vùng ô kết quả
CARD_GAP = 12             # khoảng cách dọc giữa các thẻ bên phải


def _pick_font(root: tk.Tk) -> str:
    """Ưu tiên font hiện đại nếu máy có, nếu không dùng Segoe UI."""
    available = set(tkfont.families(root))
    for name in ("Inter", "Be Vietnam Pro", "Poppins", "Segoe UI"):
        if name in available:
            return name
    return "TkDefaultFont"


def _pick_mono(root: tk.Tk) -> str:
    """Font monospace theo hệ điều hành: Consolas (Windows), Menlo (macOS)."""
    available = set(tkfont.families(root))
    for name in ("Consolas", "Menlo", "DejaVu Sans Mono", "Courier New"):
        if name in available:
            return name
    return "TkFixedFont"


class CipherPanel(ttk.Frame):
    """Một tab ứng với một thuật toán."""

    def __init__(self, parent, root: tk.Tk, algorithm: str, key_bits: int,
                 uses_frame: bool, modes: dict, note: str = "",
                 can_visualize: bool = False):
        super().__init__(parent, padding=20, style="Page.TFrame")
        self.root = root
        self.mono = _pick_mono(root)
        self.algorithm = algorithm
        self.key_bits = key_bits
        self.uses_frame = uses_frame
        self.modes = modes                      # {nhãn hiển thị: mode_id}
        self.controller = CipherController()
        self.messages: queue.Queue = queue.Queue()
        self.busy = False
        self.closed = False
        self.controls: list = []                # (widget, trạng thái khi rảnh)
        self.can_visualize = can_visualize      # chỉ Tiny A5/1 có trực quan hóa
        self.visualize = tk.BooleanVar(value=False)
        self.visualizer = None                  # cửa sổ trực quan hóa đang mở
        self._pending_args = None               # tham số của lần xử lý đang chạy

        self.operation = tk.StringVar(value="Mã hóa")
        self.mode = tk.StringVar(value=next(iter(modes)))
        self.key = tk.StringVar()
        self.frame = tk.StringVar(value="0")
        self.ciphertext_format = tk.StringVar(value="Nhị phân (Binary)")
        self.file_path = tk.StringVar(value="Chưa chọn tệp")
        self.key_label = tk.StringVar()
        self.input_label = tk.StringVar()
        self.result_label = tk.StringVar(value="Chưa có kết quả")
        self.status = tk.StringVar(value="Nhập dữ liệu và khóa để bắt đầu.")
        self.note = note

        self._build()
        for variable in (self.operation, self.mode, self.key, self.frame, self.ciphertext_format):
            variable.trace_add("write", self.parameters_changed)
        self.parameters_changed()

    # ------------------------------------------------------------------
    # Dựng giao diện
    # ------------------------------------------------------------------
    @staticmethod
    def _card(parent) -> tuple[tk.Frame, ttk.Frame]:
        """Thẻ trắng có viền mảnh. Trả về (khung ngoài để grid, khung trong để đặt widget)."""
        outer = tk.Frame(parent, background=CARD, highlightbackground=BORDER,
                         highlightcolor=BORDER, highlightthickness=1, bd=0)
        inner = ttk.Frame(outer, padding=18, style="Card.TFrame")
        inner.pack(fill="both", expand=True)
        return outer, inner

    @staticmethod
    def _field(parent, row: int, label: str) -> ttk.Frame:
        """Một trường trong thẻ Tùy chọn: nhãn đậm phía trên, widget phía dưới."""
        group = ttk.Frame(parent)
        group.grid(row=row, column=0, sticky="ew", pady=(18, 0))
        group.columnconfigure(0, weight=1)
        ttk.Label(group, text=label, style="Field.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        return group

    def _text_box(self, parent, height: int, **extra) -> ScrolledText:
        """Ô văn bản nhiều dòng: nền trắng, viền mảnh, viền xanh khi focus."""
        return ScrolledText(parent, height=height, relief="flat", borderwidth=0,
                            highlightthickness=1, highlightbackground=BORDER,
                            highlightcolor=PRIMARY, padx=14, pady=12,
                            background=CARD, foreground=TEXT,
                            insertbackground=PRIMARY, selectbackground=PRIMARY_SOFT,
                            selectforeground=TEXT, **extra)

    def _build(self) -> None:
        self.columnconfigure(0, minsize=330)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ---- Cột trái: thẻ "Tùy chọn" -----------------------------------
        side_outer, side = self._card(self)
        side_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        side.columnconfigure(0, weight=1)
        side.rowconfigure(6, weight=1)
        ttk.Label(side, text="Tùy chọn", style="Heading.TLabel").grid(row=0, column=0, sticky="w")

        # Chức năng: hai nút chuyển (dùng chung biến với Combobox cũ)
        group = self._field(side, 1, "Chức năng")
        segment = ttk.Frame(group)
        segment.grid(row=1, column=0, sticky="ew")
        for column, name in enumerate(OPERATIONS):
            segment.columnconfigure(column, weight=1, uniform="segment")
            button = ttk.Radiobutton(segment, text=name, value=name, variable=self.operation,
                                     style="Segment.Toolbutton")
            button.grid(row=0, column=column, sticky="ew")
            self.controls.append((button, "normal"))

        # Kiểu đầu vào
        group = self._field(side, 2, "Kiểu đầu vào")
        mode_box = ttk.Combobox(group, textvariable=self.mode, values=list(self.modes), state="readonly")
        mode_box.grid(row=1, column=0, sticky="ew")
        self.controls.append((mode_box, "readonly"))

        if self.uses_frame:
            group = self._field(side, 3, "Số khung (22 bit, 0 – 4194303)")
            frame_entry = ttk.Entry(group, textvariable=self.frame)
            frame_entry.grid(row=1, column=0, sticky="ew")
            self.controls.append((frame_entry, "normal"))

            group = self._field(side, 4, "Định dạng bản mã (khi giải mã)")
            self.format_box = ttk.Combobox(
                group, textvariable=self.ciphertext_format,
                values=("Nhị phân (Binary)", "Thập lục phân (Hex)"), state="readonly")
            self.format_box.grid(row=1, column=0, sticky="ew")
            self.controls.append((self.format_box, "readonly"))

        if self.can_visualize:
            group = ttk.Frame(side)
            group.grid(row=5, column=0, sticky="ew", pady=(22, 0))
            group.columnconfigure(0, weight=1)
            ttk.Separator(group, orient="horizontal").grid(row=0, column=0, sticky="ew", pady=(0, 14))
            check = ttk.Checkbutton(group, variable=self.visualize, style="Viz.TCheckbutton",
                                    text="Hiển thị trực quan hóa quá trình\nmã hóa / giải mã")
            check.grid(row=1, column=0, sticky="w")
            ttk.Label(group, style="Muted.TLabel", wraplength=290, justify="left",
                      text="Sau khi bấm Mã hóa / Giải mã, mở cửa sổ mô phỏng từng bước "
                           "quay X, Y, Z và sinh bit khóa dòng.").grid(row=2, column=0, sticky="w", pady=(6, 0))
            self.controls.append((check, "normal"))

        if self.note:
            ttk.Label(side, text=self.note, style="Muted.TLabel", wraplength=290, justify="left").grid(
                row=6, column=0, sticky="sw", pady=(24, 0))

        # ---- Cột phải: Khóa / Dữ liệu vào / Kết quả ------------------------
        right = ttk.Frame(self, style="Page.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        # Khóa và dữ liệu vào giữ nguyên chiều cao; thẻ kết quả ăn hết phần dư.
        right.rowconfigure(0, weight=0)
        right.rowconfigure(1, weight=0)
        right.rowconfigure(2, weight=1, minsize=RESULT_MIN_SIZE + 80)

        # Thẻ khóa
        key_outer, key_card = self._card(right)
        key_outer.grid(row=0, column=0, sticky="ew")
        key_card.columnconfigure(0, weight=1)
        ttk.Label(key_card, textvariable=self.key_label, style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w")
        key_entry = ttk.Entry(key_card, textvariable=self.key, font=(self.mono, FS_MONO))
        key_entry.grid(row=1, column=0, sticky="ew", padx=(0, 12), pady=(12, 0))
        random_button = ttk.Button(key_card, text="Tạo khóa", command=self.random_key,
                                   style="Outline.TButton")
        random_button.grid(row=1, column=1, pady=(12, 0))
        self.controls.extend([(key_entry, "normal"), (random_button, "normal")])

        # Thẻ dữ liệu đầu vào (ô nhập văn bản hoặc chọn tệp) + nút xử lý + tiến trình
        input_outer, input_card = self._card(right)
        input_outer.grid(row=1, column=0, sticky="ew", pady=(CARD_GAP, 0))
        input_card.columnconfigure(0, weight=1)
        ttk.Label(input_card, textvariable=self.input_label, style="Heading.TLabel").grid(
            row=0, column=0, sticky="w")
        self.text_input = self._text_box(input_card, height=INPUT_HEIGHT, wrap="word",
                                         font=(self.mono, FS_MONO))
        self.text_input.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.controls.append((self.text_input, "normal"))
        self.file_frame = ttk.Frame(input_card)
        self.file_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.file_frame.columnconfigure(0, weight=1)
        ttk.Entry(self.file_frame, textvariable=self.file_path, state="readonly").grid(
            row=0, column=0, sticky="ew", padx=(0, 12))
        choose = ttk.Button(self.file_frame, text="Chọn tệp…", command=self.choose_file,
                            style="Outline.TButton")
        choose.grid(row=0, column=1)
        self.controls.append((choose, "normal"))

        actions = ttk.Frame(input_card)
        actions.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        actions.columnconfigure(1, weight=1)
        self.process_button = ttk.Button(actions, text="Mã hóa", command=self.process,
                                         style="Primary.TButton")
        self.process_button.grid(row=0, column=0)
        self.controls.append((self.process_button, "normal"))
        self.progress = ttk.Progressbar(actions, mode="indeterminate", style="Blue.Horizontal.TProgressbar")
        self.progress.grid(row=0, column=1, sticky="ew", padx=(20, 0))

        # Thẻ kết quả (khung lớn, co giãn theo cửa sổ)
        result_outer, result_card = self._card(right)
        result_outer.grid(row=2, column=0, sticky="nsew", pady=(CARD_GAP, 0))
        result_card.columnconfigure(0, weight=1)
        result_card.rowconfigure(1, weight=1, minsize=RESULT_MIN_SIZE)
        ttk.Label(result_card, textvariable=self.result_label, style="Heading.TLabel").grid(
            row=0, column=0, sticky="w")
        result_actions = ttk.Frame(result_card)
        result_actions.grid(row=0, column=1, sticky="e")
        self.save_button = ttk.Button(result_actions, text="Lưu kết quả thành .txt…", command=self.save,
                                      state="disabled", style="Outline.TButton")
        self.copy_button = ttk.Button(result_actions, text="Sao chép kết quả", command=self.copy_result,
                                      state="disabled", style="Outline.TButton")
        self.save_button.pack(side="left", padx=(0, 10))
        self.copy_button.pack(side="left")
        self.output = self._text_box(result_card, height=RESULT_HEIGHT, wrap="char",
                                     font=(self.mono, FS_MONO), state="disabled")
        self.output.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(12, 0))

        # Thanh trạng thái
        ttk.Label(self, textvariable=self.status, style="Status.TLabel", wraplength=1000).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(12, 0))

    # ------------------------------------------------------------------
    # Trạng thái giao diện
    # ------------------------------------------------------------------
    def _mode_id(self) -> str:
        return self.modes[self.mode.get()]

    def _show_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def parameters_changed(self, *_args) -> None:
        """Đổi tham số thì bỏ kết quả cũ để tránh lưu/sao chép nhầm."""
        if self.busy:
            return
        self.controller.clear_result()
        self._show_output("")
        self.save_button.configure(state="disabled")
        self.copy_button.configure(state="disabled")
        self.result_label.set("Chưa có kết quả")
        typed = len(self.controller.cipher.clean_binary(self.key.get()))
        self.key_label.set(f"Khóa nhị phân · {typed} / {self.key_bits} bit")
        mode = self._mode_id()
        operation = OPERATIONS[self.operation.get()]
        self.input_label.set(INPUT_LABELS[(mode, operation)])
        if self.uses_frame:
            if operation == DECRYPT and mode != MODE_FILE:
                self.format_box.master.grid()
                if self.ciphertext_format.get() == "Thập lục phân (Hex)":
                    self.input_label.set("Bản mã (hex, các ký tự 0–9 và A–F)")
                else:
                    self.input_label.set("Bản mã (chuỗi bit 0/1)")
            else:
                self.format_box.master.grid_remove()
        self.process_button.configure(text=self.operation.get() + (" tệp" if mode == MODE_FILE else ""))
        if mode == MODE_FILE:
            self.text_input.grid_remove()
            self.file_frame.grid()
            self.save_button.pack(side="left", padx=(0, 10), before=self.copy_button)
        else:
            self.file_frame.grid_remove()
            self.text_input.grid()
            self.save_button.pack_forget()
        self.status.set("Sẵn sàng xử lý.")

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        for widget, normal_state in self.controls:
            widget.configure(state="disabled" if busy else normal_state)
        self.save_button.configure(state="disabled")
        self.copy_button.configure(state="disabled")
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress["value"] = 0

    # ------------------------------------------------------------------
    # Hành động
    # ------------------------------------------------------------------
    def random_key(self) -> None:
        self.key.set(self.controller.cipher.generate_key_binary(self.algorithm))

    def choose_file(self) -> None:
        filename = filedialog.askopenfilename(
            parent=self.root, title="Chọn tệp TXT",
            filetypes=[("Văn bản TXT", "*.txt"), ("Tất cả tệp", "*")])
        if not filename:
            return
        try:
            path = self.controller.select_file(filename)
        except (ValueError, OSError) as exc:
            messagebox.showerror("Không mở được tệp", str(exc), parent=self.root)
            return
        self.file_path.set(str(path))
        self.parameters_changed()

    def process(self) -> None:
        if self.busy:
            return
        # Chụp dữ liệu trên luồng giao diện; luồng nền chỉ nhận dữ liệu thuần.
        args = (self.algorithm, self._mode_id(), OPERATIONS[self.operation.get()],
                self.key.get(), self.frame.get(), self.text_input.get("1.0", "end-1c"),
                "hex" if self.ciphertext_format.get() == "Thập lục phân (Hex)" else "binary")
        self._pending_args = args
        self.parameters_changed()
        self._set_busy(True)
        self.status.set("Đang xử lý…")
        threading.Thread(target=self._worker, args=args, daemon=True).start()
        self.root.after(80, self._poll_result)

    def _worker(self, *args) -> None:
        try:
            self.messages.put((True, self.controller.run(*args)))
        except (ValueError, OSError) as exc:
            self.messages.put((False, str(exc)))
        except Exception as exc:  # lỗi không lường trước vẫn phải báo cho người dùng
            self.messages.put((False, f"Không xử lý được: {exc}"))

    def _poll_result(self) -> None:
        if self.closed:
            return
        try:
            success, payload = self.messages.get_nowait()
        except queue.Empty:
            self.root.after(80, self._poll_result)
            return
        self._set_busy(False)
        if not success:
            self.status.set(payload)
            messagebox.showerror("Không xử lý được", payload, parent=self.root)
            return
        view: OutputView = payload
        self._last_copy = view.copy_text
        self._show_output(view.text)
        self.copy_button.configure(state="normal")
        if view.file_result is not None:
            self.result_label.set(f"{view.file_result.filename} · {len(view.file_result.data):,} byte")
            self.save_button.configure(state="normal")
            self.status.set("Đã xử lý xong. Bạn có thể lưu tệp kết quả.")
        else:
            self.result_label.set("Kết quả")
            self.status.set("Đã xử lý xong.")
        if self.can_visualize and self.visualize.get():
            self.show_visualization(self._pending_args)

    def show_visualization(self, args) -> None:
        """Mở cửa sổ mô phỏng Tiny A5/1 với đúng khóa / dữ liệu vừa xử lý."""
        _algorithm, mode, operation, key, _frame, text, _fmt = args
        try:
            key_bits = self.controller.cipher.clean_binary(key)
            if mode == MODE_CHARS and operation == ENCRYPT:
                data_bits = letters_to_bits(text)           # A–H -> 3 bit mỗi chữ
            else:
                data_bits = self.controller.cipher.clean_binary(text)
            self.close_visualizer()
            self.visualizer = open_visualizer(self.root, key_bits, data_bits,
                                              decrypt=(operation == DECRYPT))
        except ValueError as exc:
            self.status.set(f"Không mở được trực quan hóa: {exc}")

    def close_visualizer(self) -> None:
        if self.visualizer is not None and self.visualizer.winfo_exists():
            self.visualizer.close()
        self.visualizer = None

    def save(self) -> None:
        result = self.controller.result
        if self.busy or result is None:
            return
        filename = filedialog.asksaveasfilename(
            parent=self.root, title="Lưu tệp kết quả", defaultextension=".txt",
            initialdir=str(self.controller.input_path.parent), initialfile=result.filename,
            filetypes=[("Văn bản TXT", "*.txt")], confirmoverwrite=True)
        if not filename:
            return
        try:
            path = self.controller.save_result(filename)
        except (ValueError, OSError) as exc:
            messagebox.showerror("Không lưu được tệp", str(exc), parent=self.root)
            return
        self.status.set(f"Đã lưu: {path}")

    def copy_result(self) -> None:
        if self.busy or not getattr(self, "_last_copy", None):
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self._last_copy)
        self.status.set("Đã sao chép kết quả.")

    def shutdown(self) -> None:
        self.closed = True
        self.close_visualizer()


class App:
    """Cửa sổ chính chứa hai tab."""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("A5/1 — Mã hóa và giải mã")
        root.geometry("1220x980")
        root.minsize(1040, 840)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._style()

        header = ttk.Frame(root, padding=(32, 20, 32, 0), style="Page.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="A5/1 · Mã hóa & giải mã", style="Title.TLabel").pack(anchor="w")

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=20, pady=(12, 16))
        self.panels = [
            CipherPanel(
                notebook, root, ALGO_A51, key_bits=64, uses_frame=True,
                modes={"Chuỗi bit nhị phân": MODE_BINARY,
                       "Văn bản": MODE_TEXT,
                       "Tải tệp .txt": MODE_FILE},
                note="Khi giải mã, dùng đúng khóa và số khung đã dùng để mã hóa."),
            CipherPanel(
                notebook, root, ALGO_TINY, key_bits=23, uses_frame=False,
                modes={"Chuỗi bit nhị phân": MODE_BINARY,
                       "Ký tự": MODE_CHARS},
                can_visualize=True,
                note="Khóa có thể gõ dạng 100101.01001110.100110000.\n\n"
                     "Ký tự: A=000, B=001, C=010, D=011, E=100, F=101, G=110, H=111."),
        ]
        notebook.add(self.panels[0], text="  A5/1 đầy đủ  ")
        notebook.add(self.panels[1], text="  Tiny A5/1  ")

    def _style(self) -> None:
        root = self.root
        family = _pick_font(root)
        style = ttk.Style(root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        root.configure(background=PAGE)
        # Danh sách thả xuống của Combobox
        root.option_add("*TCombobox*Listbox.font", (family, FS_BODY))
        root.option_add("*TCombobox*Listbox.background", CARD)
        root.option_add("*TCombobox*Listbox.foreground", TEXT)
        root.option_add("*TCombobox*Listbox.selectBackground", PRIMARY)
        root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

        # --- Khung & nhãn -------------------------------------------------
        style.configure("TFrame", background=CARD)
        style.configure("Card.TFrame", background=CARD)
        style.configure("Page.TFrame", background=PAGE)
        style.configure("TLabel", background=CARD, foreground=TEXT, font=(family, FS_BODY))
        style.configure("Field.TLabel", font=(family, FS_LABEL, "bold"), foreground=MUTED)
        style.configure("Heading.TLabel", font=(family, FS_HEADING, "bold"))
        style.configure("Muted.TLabel", foreground=MUTED, font=(family, FS_SMALL))
        style.configure("Title.TLabel", background=PAGE, foreground=TEXT, font=(family, FS_TITLE, "bold"))
        style.configure("Status.TLabel", background=PAGE, foreground=TEXT, font=(family, FS_LABEL))

        # --- Ô nhập & Combobox ------------------------------------------
        for name in ("TEntry", "TCombobox"):
            style.configure(name, fieldbackground=CARD, foreground=TEXT, padding=10,
                            bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                            insertcolor=PRIMARY, font=(family, FS_BODY))
            style.map(name,
                      bordercolor=[("focus", PRIMARY)],
                      lightcolor=[("focus", PRIMARY)],
                      darkcolor=[("focus", PRIMARY)])
        style.map("TEntry",
                  fieldbackground=[("readonly", DISABLED_BG), ("disabled", DISABLED_BG)],
                  foreground=[("disabled", DISABLED_FG)])
        style.configure("TCombobox", background=CARD, arrowcolor=MUTED, arrowsize=16)
        style.map("TCombobox",
                  fieldbackground=[("readonly", CARD), ("disabled", DISABLED_BG)],
                  foreground=[("disabled", DISABLED_FG)],
                  selectbackground=[("readonly", CARD)],
                  selectforeground=[("readonly", TEXT)],
                  background=[("active", CARD), ("disabled", DISABLED_BG)],
                  arrowcolor=[("disabled", DISABLED_FG), ("hover", PRIMARY)])

        # --- Tickbox ----------------------------------------------------------
        style.configure("Viz.TCheckbutton", background=CARD, foreground=TEXT,
                        font=(family, FS_BODY, "bold"), focuscolor=CARD, padding=(2, 4))
        style.map("Viz.TCheckbutton",
                  background=[("active", CARD)],
                  foreground=[("disabled", DISABLED_FG)],
                  indicatorcolor=[("selected", PRIMARY), ("!selected", CARD)],
                  indicatorbackground=[("selected", PRIMARY), ("!selected", CARD)])

        # --- Nút chuyển Mã hóa / Giải mã ----------------------------------
        style.configure("Segment.Toolbutton", font=(family, FS_BODY, "bold"), padding=(12, 10),
                        anchor="center", background=SEG_BG, foreground=MUTED,
                        bordercolor=BORDER, lightcolor=SEG_BG, darkcolor=SEG_BG,
                        focuscolor=SEG_BG, relief="flat", borderwidth=1)
        style.map("Segment.Toolbutton",
                  background=[("selected", PRIMARY), ("active", "#e1e6ee")],
                  foreground=[("selected", "#ffffff"), ("disabled", DISABLED_FG)],
                  lightcolor=[("selected", PRIMARY)],
                  darkcolor=[("selected", PRIMARY)],
                  bordercolor=[("selected", PRIMARY)])

        # --- Nút: chính (xanh đặc) và phụ (viền xanh, nền trắng) ----------
        style.configure("Primary.TButton", font=(family, FS_BODY, "bold"), padding=(26, 11),
                        background=PRIMARY, foreground="#ffffff", borderwidth=1,
                        bordercolor=PRIMARY, lightcolor=PRIMARY, darkcolor=PRIMARY,
                        focuscolor=PRIMARY, relief="flat")
        style.map("Primary.TButton",
                  background=[("disabled", "#b8d4fb"), ("pressed", PRIMARY_DARK), ("active", PRIMARY_DARK)],
                  bordercolor=[("disabled", "#b8d4fb"), ("active", PRIMARY_DARK)],
                  lightcolor=[("disabled", "#b8d4fb"), ("active", PRIMARY_DARK)],
                  darkcolor=[("disabled", "#b8d4fb"), ("active", PRIMARY_DARK)],
                  foreground=[("disabled", "#ffffff")])

        for name in ("TButton", "Outline.TButton"):
            style.configure(name, font=(family, FS_BODY), padding=(18, 10),
                            background=CARD, foreground=PRIMARY, borderwidth=1,
                            bordercolor=PRIMARY, lightcolor=PRIMARY, darkcolor=PRIMARY,
                            focuscolor=CARD, relief="flat")
            style.map(name,
                      background=[("disabled", CARD), ("pressed", PRIMARY_SOFT), ("active", PRIMARY_SOFT)],
                      foreground=[("disabled", DISABLED_FG)],
                      bordercolor=[("disabled", BORDER)],
                      lightcolor=[("disabled", BORDER)],
                      darkcolor=[("disabled", BORDER)])

        # --- Thanh tiến trình ---------------------------------------------
        style.configure("Blue.Horizontal.TProgressbar", background=PRIMARY, troughcolor=PRIMARY_SOFT,
                        bordercolor=PRIMARY_SOFT, lightcolor=PRIMARY, darkcolor=PRIMARY, thickness=8)

        # --- Tab ------------------------------------------------------------
        style.configure("TNotebook", background=PAGE, borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure("TNotebook.Tab", font=(family, FS_BODY, "bold"), padding=(16, 9),
                        background="#e4e8ee", foreground=MUTED,
                        bordercolor=BORDER, lightcolor="#e4e8ee", darkcolor="#e4e8ee", borderwidth=1)
        # Tab đang chọn: nền trùng nền trang, chữ xanh, diện tích lớn hơn.
        style.map("TNotebook.Tab",
                  padding=[("selected", (26, 12)), ("!selected", (16, 8))],
                  background=[("selected", PAGE), ("!selected", "#e4e8ee")],
                  foreground=[("selected", PRIMARY), ("!selected", MUTED)],
                  lightcolor=[("selected", PAGE)],
                  darkcolor=[("selected", PAGE)])

    def close(self) -> None:
        for panel in self.panels:
            panel.shutdown()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()