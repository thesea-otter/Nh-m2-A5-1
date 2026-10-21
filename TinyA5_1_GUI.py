# TinyA5/1: X (6 bit), Y (8 bit), Z (9 bit), khóa K 23 bit
# Backend + giao diện Tkinter

import random
import tkinter as tk


# =========================
# KIỂM TRA ĐẦU VÀO
# =========================

def la_nhi_phan(chuoi):
    if chuoi == "":
        return False

    for c in chuoi:
        if c != "0" and c != "1":
            return False

    return True


def kiem_tra_dau_vao(P, K):
    if not la_nhi_phan(K):
        return "Khóa K phải là chuỗi nhị phân (chỉ gồm 0 và 1)."

    if len(K) != 23:
        return f"Khóa K phải có đúng 23 bit (hiện có {len(K)} bit)."

    if not la_nhi_phan(P):
        return "Dữ liệu đầu vào phải là chuỗi nhị phân (chỉ gồm 0 và 1)."

    return ""


# =========================
# THUẬT TOÁN TinyA5/1
# =========================

def phan_bo_khoa(K):
    # Chia khóa 23 bit thành 3 thanh ghi:
    # X = 6 bit, Y = 8 bit, Z = 9 bit

    X = [int(b) for b in K[0:6]]
    Y = [int(b) for b in K[6:14]]
    Z = [int(b) for b in K[14:23]]

    return X, Y, Z


def maj(a, b, c):
    # Hàm chiếm đa số
    return 1 if a + b + c >= 2 else 0


def quay_X(X):
    t = X[2] ^ X[4] ^ X[5]

    for j in range(5, 0, -1):
        X[j] = X[j - 1]

    X[0] = t


def quay_Y(Y):
    t = Y[6] ^ Y[7]

    for j in range(7, 0, -1):
        Y[j] = Y[j - 1]

    Y[0] = t


def quay_Z(Z):
    t = Z[2] ^ Z[7] ^ Z[8]

    for j in range(8, 0, -1):
        Z[j] = Z[j - 1]

    Z[0] = t


def sinh_bit(X, Y, Z):
    # Lấy bit điều khiển clock
    m = maj(X[1], Y[3], Z[3])

    if X[1] == m:
        quay_X(X)

    if Y[3] == m:
        quay_Y(Y)

    if Z[3] == m:
        quay_Z(Z)

    return X[5] ^ Y[7] ^ Z[8]


def sinh_chuoi_khoa(K, n):
    X, Y, Z = phan_bo_khoa(K)

    return [sinh_bit(X, Y, Z) for _ in range(n)]


def xor_bit(a, b):
    return ''.join(
        str(int(x) ^ int(y))
        for x, y in zip(a, b)
    )


def ma_hoa(P, K):
    S = ''.join(
        str(b)
        for b in sinh_chuoi_khoa(K, len(P))
    )

    return xor_bit(P, S)


def giai_ma(C, K):
    return ma_hoa(C, K)


# =========================
# GIAO DIỆN
# =========================

cua_so = tk.Tk()

cua_so.title("Hệ mã TinyA5/1")

cua_so.resizable(False, False)


# Chế độ
che_do = tk.StringVar(value="ma_hoa")


# Nhãn
nhan_K = tk.StringVar(
    value="Khóa K (0/23 bit):"
)

nhan_P = tk.StringVar(
    value="Bản rõ P:"
)

nhan_kq = tk.StringVar(
    value="Bản mã C:"
)


# Ô dữ liệu
o_K = tk.StringVar()
o_P = tk.StringVar()
o_S = tk.StringVar()
o_kq = tk.StringVar()
o_kiem_tra = tk.StringVar()
thong_bao_loi = tk.StringVar()


# =========================
# CẬP NHẬT SỐ BIT KHÓA
# =========================

def dem_bit(*_):
    nhan_K.set(
        f"Khóa K ({len(o_K.get().strip())}/23 bit):"
    )


# =========================
# ĐỔI CHẾ ĐỘ
# =========================

def doi_che_do():

    if che_do.get() == "ma_hoa":

        nhan_P.set("Bản rõ P:")
        nhan_kq.set("Bản mã C:")

    else:

        nhan_P.set("Bản mã C:")
        nhan_kq.set("Bản rõ P:")

    # Xóa kết quả cũ
    o_S.set("")
    o_kq.set("")
    o_kiem_tra.set("")
    thong_bao_loi.set("")


# =========================
# SINH KHÓA NGẪU NHIÊN
# =========================

def khoa_ngau_nhien():

    o_K.set(
        ''.join(
            random.choice("01")
            for _ in range(23)
        )
    )


# =========================
# THỰC HIỆN
# =========================

def thuc_hien():

    K = o_K.get().strip()
    P = o_P.get().strip()

    # Kiểm tra dữ liệu
    loi = kiem_tra_dau_vao(P, K)

    if loi != "":

        thong_bao_loi.set("Lỗi: " + loi)

        o_S.set("")
        o_kq.set("")
        o_kiem_tra.set("")

        return

    thong_bao_loi.set("")

    # Sinh khóa dòng
    o_S.set(
        ''.join(
            str(b)
            for b in sinh_chuoi_khoa(K, len(P))
        )
    )

    # =====================
    # MÃ HÓA
    # =====================

    if che_do.get() == "ma_hoa":

        C = ma_hoa(P, K)

        o_kq.set(C)

        # Kiểm tra bằng cách giải mã lại
        P2 = giai_ma(C, K)

        if P2 == P:
            o_kiem_tra.set(
                "✓ Giải mã kiểm tra trùng bản rõ"
            )
        else:
            o_kiem_tra.set(
                "✗ Giải mã kiểm tra không khớp"
            )

    # =====================
    # GIẢI MÃ
    # =====================

    else:

        o_kq.set(
            giai_ma(P, K)
        )

        o_kiem_tra.set("")


# Theo dõi số bit của K
o_K.trace_add("write", dem_bit)


# =========================
# BỐ CỤC GIAO DIỆN
# =========================

tk.Radiobutton(
    cua_so,
    text="Mã hóa",
    variable=che_do,
    value="ma_hoa",
    command=doi_che_do
).grid(
    row=0,
    column=0,
    sticky="w",
    padx=10,
    pady=(10, 0)
)


tk.Radiobutton(
    cua_so,
    text="Giải mã",
    variable=che_do,
    value="giai_ma",
    command=doi_che_do
).grid(
    row=0,
    column=1,
    sticky="w",
    pady=(10, 0)
)


# Khóa K
tk.Label(
    cua_so,
    textvariable=nhan_K
).grid(
    row=1,
    column=0,
    columnspan=2,
    sticky="w",
    padx=10,
    pady=(8, 0)
)


tk.Entry(
    cua_so,
    textvariable=o_K,
    width=56,
    font=("Consolas", 10)
).grid(
    row=2,
    column=0,
    columnspan=2,
    padx=10
)


# P / C
tk.Label(
    cua_so,
    textvariable=nhan_P
).grid(
    row=3,
    column=0,
    columnspan=2,
    sticky="w",
    padx=10,
    pady=(8, 0)
)


tk.Entry(
    cua_so,
    textvariable=o_P,
    width=56,
    font=("Consolas", 10)
).grid(
    row=4,
    column=0,
    columnspan=2,
    padx=10
)


# Nút thực hiện
tk.Button(
    cua_so,
    text="Thực hiện",
    command=thuc_hien,
    width=14
).grid(
    row=5,
    column=0,
    padx=10,
    pady=10,
    sticky="w"
)


# Nút khóa ngẫu nhiên
tk.Button(
    cua_so,
    text="Khóa ngẫu nhiên",
    command=khoa_ngau_nhien
).grid(
    row=5,
    column=1,
    sticky="w"
)


# Thông báo lỗi
tk.Label(
    cua_so,
    textvariable=thong_bao_loi,
    fg="red",
    wraplength=420,
    justify="left"
).grid(
    row=6,
    column=0,
    columnspan=2,
    sticky="w",
    padx=10
)


# Khóa dòng S
tk.Label(
    cua_so,
    text="Khóa dòng S:"
).grid(
    row=7,
    column=0,
    columnspan=2,
    sticky="w",
    padx=10
)


tk.Entry(
    cua_so,
    textvariable=o_S,
    width=56,
    font=("Consolas", 10),
    state="readonly"
).grid(
    row=8,
    column=0,
    columnspan=2,
    padx=10
)


# Kết quả
tk.Label(
    cua_so,
    textvariable=nhan_kq
).grid(
    row=9,
    column=0,
    columnspan=2,
    sticky="w",
    padx=10,
    pady=(8, 0)
)


tk.Entry(
    cua_so,
    textvariable=o_kq,
    width=56,
    font=("Consolas", 10),
    state="readonly"
).grid(
    row=10,
    column=0,
    columnspan=2,
    padx=10
)


# Kiểm tra
tk.Label(
    cua_so,
    textvariable=o_kiem_tra,
    fg="green"
).grid(
    row=11,
    column=0,
    columnspan=2,
    sticky="w",
    padx=10,
    pady=(4, 10)
)


# =========================
# CHẠY
# =========================

cua_so.mainloop()
