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


# 3. Giao diện Cửa sổ Menu Trung tâm
cua_so = tk.Tk()
cua_so.title("HỆ MÃ A5/1 & TINY A5/1 - BÀI TẬP NHÓM")
cua_so.geometry("480x350")
cua_so.resizable(False, False)
cua_so.configure(bg="#f8fafc")

# Tiêu đề chính
tk.Label(
    cua_so,
    text="HỆ MÃ DÒNG A5/1 & TINY A5/1",
    font=("Segoe UI", 15, "bold"),
    fg="#0f172a",
    bg="#f8fafc",
).pack(pady=(28, 4))

tk.Label(
    cua_so,
    text="Menu",
    font=("Segoe UI", 10),
    fg="#64748b",
    bg="#f8fafc",
).pack(pady=(0, 20))


# Hàm tạo Nút bấm gọn gàng (Đã bỏ dòng chú thích nhỏ)
def tao_nut_custom(parent, text, bg_color, fg_color, command):
  frame = tk.Frame(
      parent,
      bg=bg_color,
      cursor="hand2",
      bd=1,
      relief="solid",
      highlightbackground="#cbd5e1",
  )
  frame.pack(fill="x", pady=7, ipady=10)

  lbl_main = tk.Label(
      frame,
      text=text,
      font=("Segoe UI", 11, "bold"),
      fg=fg_color,
      bg=bg_color,
      cursor="hand2",
  )
  lbl_main.pack()

  # Đăng ký sự kiện click
  frame.bind("<Button-1>", lambda e: command())
  lbl_main.bind("<Button-1>", lambda e: command())

  return frame


# Khung chứa các nút bấm
khung_nut = tk.Frame(cua_so, bg="#f8fafc")
khung_nut.pack(fill="x", padx=45)

# Nút 1: Mở Web Trực quan hóa
tao_nut_custom(
    khung_nut,
    text="1. MỞ GIAO DIỆN TRỰC QUAN HÓA (WEB)",
    bg_color="#e0f2fe",
    fg_color="#0369a1",
    command=mo_web_truc_quan,
)

# Nút 2: Mở Giao diện Tkinter
tao_nut_custom(
    khung_nut,
    text="2. MỞ CỬA SỔ MÔ PHỎNG NHANH (TKINTER)",
    bg_color="#ffffff",
    fg_color="#334155",
    command=mo_app_tkinter_goc,
)

# Nút 3: Thoát
tao_nut_custom(
    khung_nut,
    text="❌ THOÁT CHƯƠNG TRÌNH",
    bg_color="#fef2f2",
    fg_color="#991b1b",
    command=thoat_chuong_trinh,
)

# Chạy giao diện
cua_so.mainloop()
