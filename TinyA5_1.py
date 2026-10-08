# Hệ mã TinyA5/1: X (6 bit), Y (8 bit), Z (9 bit), khóa K 23 bit
K = "11010010101100101010100"
P = "001"

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
    if len(K) != 23:
        return f"Khóa K phải có đúng 23 bit (hiện có {len(K)} bit)."
    if not la_nhi_phan(P):
        return "Bản rõ P phải là chuỗi nhị phân (chỉ gồm 0 và 1)."
    return ""

# THUẬT TOÁN

def phan_bo_khoa(K):
    # Chia khóa 23 bit thành 3 thanh ghi X, Y, Z.
    X = [int(b) for b in K[0:6]]
    Y = [int(b) for b in K[6:14]]
    Z = [int(b) for b in K[14:23]]
    return X, Y, Z

def maj(a, b, c):
    # Hàm chiếm đa số: trả về bit xuất hiện từ 2 lần trở lên.
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
    # Một bước sinh số: quay theo chiếm đa số rồi lấy 1 bit khóa dòng.
    m = maj(X[1], Y[3], Z[3])
    if X[1] == m: quay_X(X)
    if Y[3] == m: quay_Y(Y)
    if Z[3] == m: quay_Z(Z)
    return X[5] ^ Y[7] ^ Z[8]

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
    # P = C XOR S (XOR hai lần cùng S sẽ ra bản rõ)
    return ma_hoa(C, K)

# CHẠY CHƯƠNG TRÌNH

loi = kiem_tra_dau_vao(P, K)
if loi != "":
    print("LỖI:", loi)
else:
    S = ''.join(str(b) for b in sinh_chuoi_khoa(K, len(P)))
    C = ma_hoa(P, K)
    P2 = giai_ma(C, K)
    print("Khóa dòng S :", S)
    print("Bản mã   C  :", C)
    print("Giải mã  P  :", P2)