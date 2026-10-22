"""Khởi chạy cửa sổ desktop: python run_desktop.py."""

import sys


def main() -> int:
    try:
        import tkinter as tk
        from a51_desktop.app import main as launch
    except ImportError:
        print(
            "Python hiện tại chưa có Tcl/Tk hoạt động.\n"
            "Trên Windows, cài hoặc sửa cài đặt Python và bật thành phần Tcl/Tk.\n"
            "Sau đó chạy lại start_windows.bat.",
            file=sys.stderr,
        )
        return 1
    try:
        launch()
    except tk.TclError as exc:
        print(f"Không mở được cửa sổ ứng dụng: {exc}", file=sys.stderr)
        print("Hãy chạy trên máy có môi trường desktop và Tcl/Tk hoạt động.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
