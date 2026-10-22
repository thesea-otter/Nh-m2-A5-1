import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import webbrowser

# Nhập ứng dụng Flask từ app.py
try:
  from app import app
except ImportError:
  pass


# 1. Chạy Flask Server ẩn dưới nền bằng Threading
def start_flask():
  try:
    app.run(port=5000, debug=False, use_reloader=False)
  except Exception as e:
    print(f"Lỗi khởi chạy Flask: {e}")


flask_thread = threading.Thread(target=start_flask, daemon=True)
flask_thread.start()


# 2. Các hàm xử lý sự kiện
def mo_web_truc_quan():
  webbrowser.open("http://127.0.0.1:5000")


def mo_app_tkinter_goc():
  # Gọi chạy file Tkinter gốc
  script_dir = os.path.dirname(os.path.abspath(__file__))
  target_file = os.path.join(script_dir, "Backend fronted a5_1.py")
  if os.path.exists(target_file):
    os.system(f'python3 "{target_file}"')
  else:
    messagebox.showerror(
        "Không tìm thấy file",
        "Không tìm thấy file 'Backend fronted a5_1.py' trong cùng thư mục!",
    )


def thoat_chuong_trinh():
  cua_so.destroy()
  sys.exit()


# 3. Giao diện Cửa sổ Menu Trung tâm (Tương thích hoàn hảo với macOS)
cua_so = tk.Tk()
cua_so.title("HỆ MÃ A5/1 & TINY A5/1 - BÀI TẬP NHÓM")
cua_so.geometry("520x420")
cua_so.resizable(False, False)
cua_so.configure(bg="#f8fafc")  # Nền xám trắng nhã nhặn, sang trọng

# Tiêu đề chính
tk.Label(
    cua_so,
    text="HỆ MÃ DÒNG A5/1 & TINY A5/1",
    font=("Segoe UI", 16, "bold"),
    fg="#0f172a",
    bg="#f8fafc",
).pack(pady=(30, 5))

tk.Label(
    cua_so,
    text="Trung tâm Điều khiển & Trực quan hóa Thuật toán",
    font=("Segoe UI", 11),
    fg="#475569",
    bg="#f8fafc",
).pack(pady=(0, 25))


# Tạo Custom Nút Bấm bằng Frame + Label (Bỏ qua giới hạn màu của macOS)
def tao_nut_custom(parent, text, subtext, bg_color, fg_color, command):
  frame = tk.Frame(
      parent,
      bg=bg_color,
      cursor="hand2",
      bd=1,
      relief="solid",
      highlightbackground="#cbd5e1",
  )
  frame.pack(fill="x", pady=8, ipady=8)

  lbl_main = tk.Label(
      frame,
      text=text,
      font=("Segoe UI", 11, "bold"),
      fg=fg_color,
      bg=bg_color,
      cursor="hand2",
  )
  lbl_main.pack()

  if subtext:
    lbl_sub = tk.Label(
        frame,
        text=subtext,
        font=("Segoe UI", 9),
        fg="#64748b",
        bg=bg_color,
        cursor="hand2",
    )
    lbl_sub.pack()

  # Đăng ký sự kiện click cho cả Frame lẫn Label
  for widget in (frame, lbl_main) + (
      (lbl_sub,) if subtext else ()
  ):
    widget.bind("<Button-1>", lambda e: command())

  return frame


# Khung chứa các nút bấm
khung_nut = tk.Frame(cua_so, bg="#f8fafc")
khung_nut.pack(fill="x", padx=45)

# Nút 1: Mở Web Trực quan hóa
tao_nut_custom(
    khung_nut,
    text="✨ 1. MỞ GIAO DIỆN TRỰC QUAN HÓA (WEB)",
    subtext="Mô phỏng động xoay thanh ghi & mã hóa/giải mã file",
    bg_color="#e0f2fe",  # Nền xanh nhạt nổi bật
    fg_color="#0369a1",  # Chữ xanh đậm tương phản cao
    command=mo_web_truc_quan,
)

# Nút 2: Mở Giao diện Tkinter
tao_nut_custom(
    khung_nut,
    text="🖥️ 2. MỞ CỬA SỔ MÔ PHỎNG NHANH (TKINTER)",
    subtext="Giao diện cửa sổ ứng dụng desktop gốc",
    bg_color="#ffffff",  # Nền trắng
    fg_color="#334155",  # Chữ ghi xám đậm
    command=mo_app_tkinter_goc,
)

# Nút 3: Thoát
tao_nut_custom(
    khung_nut,
    text="❌ THOÁT CHƯƠNG TRÌNH",
    subtext="",
    bg_color="#fef2f2",  # Nền đỏ nhạt
    fg_color="#991b1b",  # Chữ đỏ đậm
    command=thoat_chuong_trinh,
)

# Chạy giao diện
cua_so.mainloop()