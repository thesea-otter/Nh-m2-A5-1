from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import math

app = Flask(__name__)
# Route trả về giao diện HTML khi truy cập 127.0.0.1:5000
@app.route("/")
def index():
  return render_template("visualize.html")

# Cho phép Frontend Web truy cập API từ trình duyệt mà không bị chặn bởi CORS policy
CORS(app)


# ============================================================
# CÁC HÀM DÙNG CHUNG CHO CẢ TINY A5/1 VÀ A5/1 ĐẦY ĐỦ
# ============================================================

def la_nhi_phan(chuoi):
    """Kiểm tra chuỗi chỉ gồm ký tự '0' và '1' (và không rỗng)."""
    if chuoi == "":
        return False
    for c in chuoi:
        if c != "0" and c != "1":
            return False
    return True


def kiem_tra_dau_vao(key_str, input_str, do_dai_khoa):
    """Kiểm tra khóa và dữ liệu. Trả về thông báo lỗi, hoặc None nếu hợp lệ."""
    if len(key_str) != do_dai_khoa or not la_nhi_phan(key_str):
        return "Khóa K phải đủ " + str(do_dai_khoa) + " bit nhị phân."
    if not la_nhi_phan(input_str):
        return "Dữ liệu đầu vào phải là chuỗi nhị phân."
    return None


def maj(a, b, c):
    """Hàm chiếm đa số: trả về bit nào xuất hiện nhiều hơn trong 3 bit."""
    if a + b + c >= 2:
        return 1
    return 0


def xor_cac_bit(thanh_ghi, vi_tri):
    """XOR các bit của thanh ghi tại những vị trí cho trước."""
    ket_qua = 0
    for v in vi_tri:
        ket_qua = ket_qua ^ thanh_ghi[v]
    return ket_qua


def dich_thanh_ghi(thanh_ghi, bit_moi):
    """Dịch cả thanh ghi sang phải 1 vị trí, rồi đặt bit mới vào đầu."""
    for j in range(len(thanh_ghi) - 1, 0, -1):
        thanh_ghi[j] = thanh_ghi[j - 1]
    thanh_ghi[0] = bit_moi


def lay_bit_khoa(X, Y, Z):
    """Bit khóa = XOR bit cuối cùng của 3 thanh ghi (X[-1] là phần tử cuối)."""
    return X[-1] ^ Y[-1] ^ Z[-1]


def chay_mo_phong(X, Y, Z, input_str,
                  quay_x, quay_y, quay_z,
                  taps_x, taps_y, taps_z):
    """
    Chạy mô phỏng từng bit và ghi lại từng bước.
    - quay_x, quay_y, quay_z : vị trí bit dùng để kiểm tra quay của mỗi thanh ghi
    - taps_x, taps_y, taps_z : các vị trí bit dùng để tính bit phản hồi
    """
    steps = []
    keystream = ""
    result = ""

    # Bước 0: trạng thái ban đầu (chưa quay)
    steps.append({
        'step_index': 0,
        'X': list(X),
        'Y': list(Y),
        'Z': list(Z),
        'clock_bits': {'X': X[quay_x], 'Y': Y[quay_y], 'Z': Z[quay_z]},
        'm': None,
        'will_clock': {'X': False, 'Y': False, 'Z': False},
        'keystream_bit': lay_bit_khoa(X, Y, Z),
        'output_bit': None,
        'keystream_so_far': '',
        'result_so_far': ''
    })

    # Mỗi bit dữ liệu là một bước
    for i in range(len(input_str)):
        bit_in = int(input_str[i])

        # 1. Lấy bit kiểm tra quay và tìm bit đa số
        bx = X[quay_x]
        by = Y[quay_y]
        bz = Z[quay_z]
        m = maj(bx, by, bz)

        # 2. Thanh ghi nào có bit kiểm tra bằng m thì được quay
        will_x = (bx == m)
        will_y = (by == m)
        will_z = (bz == m)

        # 3. Tính bit phản hồi (tính trước khi quay)
        t_x = xor_cac_bit(X, taps_x)
        t_y = xor_cac_bit(Y, taps_y)
        t_z = xor_cac_bit(Z, taps_z)

        # 4. Quay các thanh ghi được phép
        if will_x:
            dich_thanh_ghi(X, t_x)
        if will_y:
            dich_thanh_ghi(Y, t_y)
        if will_z:
            dich_thanh_ghi(Z, t_z)

        # 5. Tạo bit khóa rồi XOR với bit dữ liệu
        s_i = lay_bit_khoa(X, Y, Z)
        out_bit = bit_in ^ s_i

        keystream = keystream + str(s_i)
        result = result + str(out_bit)

        steps.append({
            'step_index': i + 1,
            'input_bit': bit_in,
            'X': list(X),
            'Y': list(Y),
            'Z': list(Z),
            'clock_bits': {'X': bx, 'Y': by, 'Z': bz},
            'm': m,
            'will_clock': {'X': will_x, 'Y': will_y, 'Z': will_z},
            't_values': {'X': t_x, 'Y': t_y, 'Z': t_z},
            'keystream_bit': s_i,
            'output_bit': out_bit,
            'keystream_so_far': keystream,
            'result_so_far': result
        })

    return {
        'steps': steps,
        'final_keystream': keystream,
        'final_result': result
    }


# ============================================================
# HAI THUẬT TOÁN
# ============================================================

def simulate_tiny_a51(key_str, input_str):
    """Tiny A5/1: khóa 23 bit, X = 6 bit, Y = 8 bit, Z = 9 bit."""
    loi = kiem_tra_dau_vao(key_str, input_str, 23)
    if loi:
        return None, loi

    X = [int(b) for b in key_str[0:6]]
    Y = [int(b) for b in key_str[6:14]]
    Z = [int(b) for b in key_str[14:23]]

    ket_qua = chay_mo_phong(X, Y, Z, input_str,
                            1, 3, 3,
                            [2, 4, 5], [6, 7], [2, 7, 8])
    return ket_qua, None


def simulate_full_a51(key_str, input_str):
    """A5/1 đầy đủ: khóa 64 bit, X = 19 bit, Y = 22 bit, Z = 23 bit."""
    loi = kiem_tra_dau_vao(key_str, input_str, 64)
    if loi:
        return None, loi

    X = [int(b) for b in key_str[0:19]]
    Y = [int(b) for b in key_str[19:41]]
    Z = [int(b) for b in key_str[41:64]]

    ket_qua = chay_mo_phong(X, Y, Z, input_str,
                            8, 10, 10,
                            [13, 16, 17, 18], [20, 21], [7, 20, 21, 22])
    return ket_qua, None

@app.route('/api/simulate', methods=['POST'])
def api_simulate():
    """API tính toán các bước quay thanh ghi từ thuật toán Python lõi."""
    data = request.json or {}
    algo_key = data.get('algo_key', 'tiny')
    key_str = data.get('key', '').strip()
    input_str = data.get('data', '').strip()
    mode = data.get('mode', 'encrypt')

    if algo_key == 'tiny':
        res, err = simulate_tiny_a51(key_str, input_str, mode)
    else:
        res, err = simulate_full_a51(key_str, input_str, mode)

    if err:
        return jsonify({'success': False, 'error': err}), 400

    return jsonify({'success': True, 'data': res})

@app.route('/api/status', methods=['GET'])
def api_status():
    """API kiểm tra xem Python Backend đã hoạt động chưa."""
    return jsonify({
        'status': 'online',
        'message': 'Python A5/1 Backend Engine đang hoạt động!'
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 PYTHON BACKEND A5/1 & TINY A5/1 KHỞI CHẠY TẠI http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host='127.0.0.1', port=5000, debug=True)
