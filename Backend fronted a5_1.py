# Hệ mã A5/1: X (19 bit), Y (22 bit), Z (23 bit), khóa K 64 bit
# Backend (thuật toán) + giao diện cửa sổ nhỏ bằng tkinter (thư viện có sẵn của Python)

import random
import tkinter as tk

# KIỂM TRA ĐẦU VÀO

def la_nhi_phan(chuoi):
    # Đúng nếu chuỗi không rỗng và chỉ gồm '0' và '1'.
    if chuoi == "":
        return False
    for c in chuoi:
        if c != "0" and c != "1":
            return False
    return True

def kiem_tra_dau_vao(P, K):
    # Trả về câu thông báo lỗi; nếu mọi thứ hợp lệ thì trả về "".
    if not la_nhi_phan(K):
        return "Khóa K phải là chuỗi nhị phân (chỉ gồm 0 và 1)."
    if len(K) != 64:
        return f"Khóa K phải có đúng 64 bit (hiện có {len(K)} bit)."
    if not la_nhi_phan(P):
        return "Dữ liệu đầu vào phải là chuỗi nhị phân (chỉ gồm 0 và 1)."
    return ""

# THUẬT TOÁN

def phan_bo_khoa(K):
    # Chia khóa 64 bit thành 3 thanh ghi X, Y, Z.
    X = [int(b) for b in K[0:19]]
    Y = [int(b) for b in K[19:41]]
    Z = [int(b) for b in K[41:64]]
    return X, Y, Z

def maj(a, b, c):
    # Hàm chiếm đa số: trả về bit xuất hiện từ 2 lần trở lên.
    return 1 if a + b + c >= 2 else 0

def quay_X(X):
    t = X[13] ^ X[16] ^ X[17] ^ X[18]
    for j in range(18, 0, -1):
        X[j] = X[j - 1]
    X[0] = t

def quay_Y(Y):
    t = Y[20] ^ Y[21]
    for j in range(21, 0, -1):
        Y[j] = Y[j - 1]
    Y[0] = t

def quay_Z(Z):
    t = Z[7] ^ Z[20] ^ Z[21] ^ Z[22]
    for j in range(22, 0, -1):
        Z[j] = Z[j - 1]
    Z[0] = t

def sinh_bit(X, Y, Z):
    # Một bước sinh số: quay theo chiếm đa số rồi lấy 1 bit khóa dòng.
    m = maj(X[8], Y[10], Z[10])
    if X[8] == m: quay_X(X)
    if Y[10] == m: quay_Y(Y)
    if Z[10] == m: quay_Z(Z)
    return X[8] ^ Y[10] ^ Z[10]

def sinh_chuoi_khoa(K, n):
    # Sinh dãy khóa dòng S gồm n bit.
    X, Y, Z = phan_bo_khoa(K)
    return [sinh_bit(X, Y, Z) for _ in range(n)]

def xor_bit(a, b):
    # XOR hai chuỗi bit có cùng độ dài.
    return ''.join(str(int(x) ^ int(y)) for x, y in zip(a, b))

def ma_hoa(P, K):
    # C = P xor S
    S = ''.join(str(b) for b in sinh_chuoi_khoa(K, len(P)))
    return xor_bit(P, S)

def giai_ma(C, K):
    # P = C xor S (XOR hai lần cùng S sẽ ra bản rõ)
    return ma_hoa(C, K)

# GIAO DIỆN CỬA SỔ

cua_so = tk.Tk()
cua_so.title("Hệ mã A5/1")
cua_so.resizable(False, False)

che_do = tk.StringVar(value="ma_hoa")   # "ma_hoa" hoặc "giai_ma"
nhan_K = tk.StringVar(value="Khóa K (0/64 bit):")
nhan_P = tk.StringVar(value="Bản rõ P:")
nhan_kq = tk.StringVar(value="Bản mã C:")
o_K = tk.StringVar()
o_P = tk.StringVar()
o_S = tk.StringVar()
o_kq = tk.StringVar()
o_kiem_tra = tk.StringVar()
thong_bao_loi = tk.StringVar()

def dem_bit(*_):
    # Cập nhật số bit hiện có của khóa K.
    nhan_K.set(f"Khóa K ({len(o_K.get().strip())}/64 bit):")

def doi_che_do():
    # Đổi nhãn theo chế độ và xóa kết quả cũ.
    if che_do.get() == "ma_hoa":
        nhan_P.set("Bản rõ P:")
        nhan_kq.set("Bản mã C:")
    else:
        nhan_P.set("Bản mã C:")
        nhan_kq.set("Bản rõ P:")
    o_S.set("")
    o_kq.set("")
    o_kiem_tra.set("")
    thong_bao_loi.set("")

def khoa_ngau_nhien():
    o_K.set(''.join(random.choice("01") for _ in range(64)))

def thuc_hien():
    K = o_K.get().strip()
    P = o_P.get().strip()
    loi = kiem_tra_dau_vao(P, K)
    if loi != "":
        thong_bao_loi.set("Lỗi: " + loi)
        o_S.set("")
        o_kq.set("")
        o_kiem_tra.set("")
        return
    thong_bao_loi.set("")
    o_S.set(''.join(str(b) for b in sinh_chuoi_khoa(K, len(P))))
    if che_do.get() == "ma_hoa":
        C = ma_hoa(P, K)
        o_kq.set(C)
        P2 = giai_ma(C, K)
        o_kiem_tra.set("✓ Giải mã kiểm tra trùng bản rõ" if P2 == P else "✗ Giải mã kiểm tra không khớp")
    else:
        o_kq.set(giai_ma(P, K))
        o_kiem_tra.set("")

o_K.trace_add("write", dem_bit)

# --- Bố cục ---
tk.Radiobutton(cua_so, text="Mã hóa", variable=che_do, value="ma_hoa", command=doi_che_do).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))
tk.Radiobutton(cua_so, text="Giải mã", variable=che_do, value="giai_ma", command=doi_che_do).grid(row=0, column=1, sticky="w", pady=(10, 0))

tk.Label(cua_so, textvariable=nhan_K).grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 0))
tk.Entry(cua_so, textvariable=o_K, width=56, font=("Consolas", 10)).grid(row=2, column=0, columnspan=2, padx=10)

tk.Label(cua_so, textvariable=nhan_P).grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 0))
tk.Entry(cua_so, textvariable=o_P, width=56, font=("Consolas", 10)).grid(row=4, column=0, columnspan=2, padx=10)

tk.Button(cua_so, text="Thực hiện", command=thuc_hien, width=14).grid(row=5, column=0, padx=10, pady=10, sticky="w")
tk.Button(cua_so, text="Khóa ngẫu nhiên", command=khoa_ngau_nhien).grid(row=5, column=1, sticky="w")

tk.Label(cua_so, textvariable=thong_bao_loi, fg="red", wraplength=420, justify="left").grid(row=6, column=0, columnspan=2, sticky="w", padx=10)

tk.Label(cua_so, text="Khóa dòng S:").grid(row=7, column=0, columnspan=2, sticky="w", padx=10)
tk.Entry(cua_so, textvariable=o_S, width=56, font=("Consolas", 10), state="readonly").grid(row=8, column=0, columnspan=2, padx=10)

tk.Label(cua_so, textvariable=nhan_kq).grid(row=9, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 0))
tk.Entry(cua_so, textvariable=o_kq, width=56, font=("Consolas", 10), state="readonly").grid(row=10, column=0, columnspan=2, padx=10)

tk.Label(cua_so, textvariable=o_kiem_tra, fg="green").grid(row=11, column=0, columnspan=2, sticky="w", padx=10, pady=(4, 10))

cua_so.mainloop()