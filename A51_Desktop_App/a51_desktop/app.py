"""Giao diện desktop Tkinter. Mọi xử lý mật mã đi qua FileCryptoService."""

from __future__ import annotations

import queue
import secrets
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from a51_backend import FileCryptoError
from .controller import DesktopFileController


ALGORITHMS = {"A5/1 (bản nhóm)": "a51", "Tiny A5/1": "tiny_a51"}
OPERATIONS = {"Mã hóa": "encrypt", "Giải mã": "decrypt"}


class FileCryptoApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.controller = DesktopFileController()
        self.messages = queue.Queue()
        self.busy = False
        self.closed = False
        self.controls = []
        self.operation = tk.StringVar(value="Mã hóa")
        self.algorithm = tk.StringVar(value="A5/1 (bản nhóm)")
        self.key = tk.StringVar()
        self.file_path = tk.StringVar(value="Chưa chọn file")
        self.key_label = tk.StringVar(value="Khóa nhị phân · 0 / 64 bit")
        self.file_hint = tk.StringVar(value="Chọn văn bản UTF-8, tối đa 64 KiB.")
        self.result_label = tk.StringVar(value="Chưa có kết quả")
        self.status = tk.StringVar(value="Chọn file .txt và nhập khóa để bắt đầu.")
        root.title("A5/1 — Mã hóa và giải mã file TXT")
        root.geometry("1000x750")
        root.minsize(800, 630)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._build()
        for variable in (self.operation, self.algorithm, self.key):
            variable.trace_add("write", self.parameters_changed)

    def _build(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background="#f2f5f6")
        style.configure("TLabel", background="#f2f5f6", foreground="#20323f", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Muted.TLabel", foreground="#5d707a", font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8))
        style.configure("TCombobox", padding=7)
        style.configure("TEntry", padding=7)
        self.root.configure(background="#f2f5f6")
        main = ttk.Frame(self.root, padding=24)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(8, weight=1)
        ttk.Label(main, text="Mã hóa & giải mã file TXT", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(main, text="Ứng dụng desktop · Xử lý trực tiếp trên máy", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 20))

        choices = ttk.Frame(main)
        choices.grid(row=2, column=0, sticky="ew")
        choices.columnconfigure(0, weight=1)
        choices.columnconfigure(1, weight=1)
        for column, (label, variable, values) in enumerate([
            ("Chức năng", self.operation, list(OPERATIONS)),
            ("Thuật toán", self.algorithm, list(ALGORITHMS)),
        ]):
            group = ttk.Frame(choices, padding=(0 if column == 0 else 12, 0, 12 if column == 0 else 0, 0))
            group.grid(row=0, column=column, sticky="ew")
            group.columnconfigure(0, weight=1)
            ttk.Label(group, text=label).grid(row=0, column=0, sticky="w", pady=(0, 5))
            control = ttk.Combobox(group, textvariable=variable, values=values, state="readonly")
            control.grid(row=1, column=0, sticky="ew")
            self.controls.append((control, "readonly"))

        file_frame = ttk.Frame(main)
        file_frame.grid(row=3, column=0, sticky="ew", pady=(15, 0))
        file_frame.columnconfigure(0, weight=1)
        ttk.Label(file_frame, text="File đầu vào (.txt)").grid(row=0, column=0, sticky="w", pady=(0, 5))
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path, state="readonly")
        file_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        select_button = ttk.Button(file_frame, text="Chọn file…", command=self.choose_file)
        select_button.grid(row=1, column=1)
        self.controls.append((select_button, "normal"))
        ttk.Label(file_frame, textvariable=self.file_hint, style="Muted.TLabel").grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))

        key_frame = ttk.Frame(main)
        key_frame.grid(row=4, column=0, sticky="ew", pady=(15, 0))
        key_frame.columnconfigure(0, weight=1)
        ttk.Label(key_frame, textvariable=self.key_label).grid(row=0, column=0, sticky="w", pady=(0, 5))
        key_entry = ttk.Entry(key_frame, textvariable=self.key, font=("Consolas", 11))
        key_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        random_button = ttk.Button(key_frame, text="Tạo khóa", command=self.random_key)
        random_button.grid(row=1, column=1)
        self.controls.extend([(key_entry, "normal"), (random_button, "normal")])

        actions = ttk.Frame(main)
        actions.grid(row=5, column=0, sticky="ew", pady=(16, 0))
        self.process_button = ttk.Button(actions, text="Mã hóa file", command=self.process)
        self.process_button.pack(side="left")
        self.controls.append((self.process_button, "normal"))
        self.save_button = ttk.Button(actions, text="Lưu kết quả thành .txt…", command=self.save, state="disabled")
        self.save_button.pack(side="left", padx=10)
        self.copy_button = ttk.Button(actions, text="Sao chép kết quả", command=self.copy_result, state="disabled")
        self.copy_button.pack(side="left")
        self.progress = ttk.Progressbar(main, mode="indeterminate")
        self.progress.grid(row=6, column=0, sticky="ew", pady=(13, 10))
        ttk.Label(main, textvariable=self.result_label, style="Muted.TLabel").grid(row=7, column=0, sticky="w", pady=(0, 6))
        self.output = ScrolledText(main, wrap="word", font=("Consolas", 11), height=10, relief="solid", borderwidth=1, padx=12, pady=12, state="disabled", background="white", foreground="#20323f")
        self.output.grid(row=8, column=0, sticky="nsew")
        ttk.Label(main, textvariable=self.status, wraplength=900).grid(row=9, column=0, sticky="w", pady=(12, 0))
        ttk.Label(main, text="Khi giải mã, sử dụng đúng thuật toán và khóa đã dùng để mã hóa.", style="Muted.TLabel").grid(row=10, column=0, sticky="w", pady=(7, 0))

    def _show_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def parameters_changed(self, *_args) -> None:
        if self.busy:
            return
        self.controller.clear_result()
        self._show_output("")
        self.save_button.configure(state="disabled")
        self.copy_button.configure(state="disabled")
        self.result_label.set("Chưa có kết quả")
        length = 64 if self.algorithm.get() == "A5/1 (bản nhóm)" else 23
        self.key_label.set(f"Khóa nhị phân · {len(self.key.get().strip())} / {length} bit")
        self.file_hint.set("Chọn văn bản UTF-8, tối đa 64 KiB." if self.operation.get() == "Mã hóa" else "Chọn file .txt chứa bản mã Base64 do chương trình tạo.")
        self.process_button.configure(text=self.operation.get() + " file")
        self.status.set("Sẵn sàng xử lý file.")

    def choose_file(self) -> None:
        filename = filedialog.askopenfilename(parent=self.root, title="Chọn file TXT", filetypes=[("Văn bản TXT", "*.txt"), ("Tất cả file", "*")])
        if not filename:
            return
        try:
            path = self.controller.select_file(filename)
        except (FileCryptoError, OSError) as exc:
            messagebox.showerror("Không mở được file", str(exc), parent=self.root)
            return
        self.file_path.set(str(path))
        self.parameters_changed()

    def random_key(self) -> None:
        length = 64 if self.algorithm.get() == "A5/1 (bản nhóm)" else 23
        self.key.set(f"{secrets.randbelow((1 << length) - 1) + 1:0{length}b}")

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        for control, normal_state in self.controls:
            control.configure(state="disabled" if busy else normal_state)
        self.save_button.configure(state="disabled")
        self.copy_button.configure(state="disabled")
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress["value"] = 0

    def process(self) -> None:
        if self.busy:
            return
        if self.controller.input_path is None:
            messagebox.showerror("Chưa chọn file", "Hãy chọn một file .txt trước khi xử lý.", parent=self.root)
            return
        self.parameters_changed()
        # Chụp giá trị trên UI thread; worker chỉ nhận dữ liệu thuần Python.
        operation = OPERATIONS[self.operation.get()]
        algorithm = ALGORITHMS[self.algorithm.get()]
        key = self.key.get()
        self._set_busy(True)
        self.status.set("Đang xử lý file…")
        threading.Thread(target=self._worker, args=(operation, key, algorithm), daemon=True).start()
        self.root.after(80, self._poll_result)

    def _worker(self, operation: str, key: str, algorithm: str) -> None:
        try:
            result = self.controller.process_file(operation, key, algorithm)
            self.messages.put((True, result))
        except (FileCryptoError, OSError) as exc:
            self.messages.put((False, str(exc)))
        except Exception as exc:
            self.messages.put((False, f"Không xử lý được file: {exc}"))

    def _poll_result(self) -> None:
        if self.closed:
            return
        try:
            success, payload = self.messages.get_nowait()
        except queue.Empty:
            self.root.after(80, self._poll_result)
            return
        self._set_busy(False)
        if success:
            self._show_output(payload.content)
            self.result_label.set(f"{payload.filename} · {len(payload.data):,} byte")
            self.save_button.configure(state="normal")
            self.copy_button.configure(state="normal")
            self.status.set("Đã xử lý xong. Bạn có thể xem toàn bộ nội dung và lưu file kết quả.")
        else:
            self.status.set(payload)
            messagebox.showerror("Không xử lý được file", payload, parent=self.root)

    def save(self) -> None:
        result = self.controller.result
        if self.busy or result is None:
            return
        filename = filedialog.asksaveasfilename(
            parent=self.root, title="Lưu file kết quả", defaultextension=".txt",
            initialdir=str(self.controller.input_path.parent), initialfile=result.filename,
            filetypes=[("Văn bản TXT", "*.txt")], confirmoverwrite=True,
        )
        if not filename:
            return
        try:
            path = self.controller.save_result(filename)
        except (FileCryptoError, OSError) as exc:
            messagebox.showerror("Không lưu được file", str(exc), parent=self.root)
            return
        self.status.set(f"Đã lưu: {path}")

    def copy_result(self) -> None:
        if self.busy or self.controller.result is None:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.controller.result.content)
        self.status.set("Đã sao chép nội dung kết quả.")

    def close(self) -> None:
        self.closed = True
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    FileCryptoApp(root)
    root.mainloop()
