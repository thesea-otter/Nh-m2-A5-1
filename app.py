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

def la_nhi_phan(chuoi):
    """Kiểm tra chuỗi chỉ bao gồm bit '0' và '1'."""
    if not chuoi:
        return False
    return all(c in ('0', '1') for c in chuoi)

def maj(a, b, c):
    """Hàm chiếm đa số (Majority function)."""
    return 1 if (a + b + c) >= 2 else 0

def simulate_tiny_a51(key_str, input_str, mode='encrypt'):
    """
    Thực hiện mô phỏng từng bước thuật toán Tiny A5/1 (Key 23-bit)
    X (6 bit), Y (8 bit), Z (9 bit)
    """
    if len(key_str) != 23 or not la_nhi_phan(key_str):
        return None, "Khóa K của Tiny A5/1 phải đủ 23 bit nhị phân."
    if not la_nhi_phan(input_str):
        return None, "Dữ liệu đầu vào phải là chuỗi nhị phân."

    X = [int(b) for b in key_str[0:6]]
    Y = [int(b) for b in key_str[6:14]]
    Z = [int(b) for b in key_str[14:23]]

    steps = []
    keystream_bits = []
    result_bits = []

    # Bước 0: Trạng thái ban đầu
    steps.append({
        'step_index': 0,
        'X': list(X),
        'Y': list(Y),
        'Z': list(Z),
        'clock_bits': {'X': X[1], 'Y': Y[3], 'Z': Z[3]},
        'm': None,
        'will_clock': {'X': False, 'Y': False, 'Z': False},
        'keystream_bit': X[5] ^ Y[7] ^ Z[8],
        'output_bit': None,
        'keystream_so_far': '',
        'result_so_far': ''
    })

    for i, char_bit in enumerate(input_str):
        bit_in = int(char_bit)

        # Bit kiểm tra quay
        x1, y3, z3 = X[1], Y[3], Z[3]
        m = maj(x1, y3, z3)

        will_x = (x1 == m)
        will_y = (y3 == m)
        will_z = (z3 == m)

        # Tính bit phản hồi
        t_x = X[2] ^ X[4] ^ X[5]
        t_y = Y[6] ^ Y[7]
        t_z = Z[2] ^ Z[7] ^ Z[8]

        # Quay các thanh ghi
        if will_x:
            for j in range(5, 0, -1):
                X[j] = X[j - 1]
            X[0] = t_x

        if will_y:
            for j in range(7, 0, -1):
                Y[j] = Y[j - 1]
            Y[0] = t_y

        if will_z:
            for j in range(8, 0, -1):
                Z[j] = Z[j - 1]
            Z[0] = t_z

        # Lấy bit khóa s_i và thực hiện XOR
        s_i = X[5] ^ Y[7] ^ Z[8]
        out_bit = bit_in ^ s_i

        keystream_bits.append(str(s_i))
        result_bits.append(str(out_bit))

        steps.append({
            'step_index': i + 1,
            'input_bit': bit_in,
            'X': list(X),
            'Y': list(Y),
            'Z': list(Z),
            'clock_bits': {'X': x1, 'Y': y3, 'Z': z3},
            'm': m,
            'will_clock': {'X': will_x, 'Y': will_y, 'Z': will_z},
            't_values': {'X': t_x, 'Y': t_y, 'Z': t_z},
            'keystream_bit': s_i,
            'output_bit': out_bit,
            'keystream_so_far': "".join(keystream_bits),
            'result_so_far': "".join(result_bits)
        })

    return {
        'steps': steps,
        'final_keystream': "".join(keystream_bits),
        'final_result': "".join(result_bits)
    }, None

def simulate_full_a51(key_str, input_str, mode='encrypt'):
    """
    Thực hiện mô phỏng từng bước thuật toán A5/1 đầy đủ (Key 64-bit)
    X (19 bit), Y (22 bit), Z (23 bit)
    """
    if len(key_str) != 64 or not la_nhi_phan(key_str):
        return None, "Khóa K của A5/1 phải đủ 64 bit nhị phân."
    if not la_nhi_phan(input_str):
        return None, "Dữ liệu đầu vào phải là chuỗi nhị phân."

    X = [int(b) for b in key_str[0:19]]
    Y = [int(b) for b in key_str[19:41]]
    Z = [int(b) for b in key_str[41:64]]

    steps = []
    keystream_bits = []
    result_bits = []

    steps.append({
        'step_index': 0,
        'X': list(X),
        'Y': list(Y),
        'Z': list(Z),
        'clock_bits': {'X': X[8], 'Y': Y[10], 'Z': Z[10]},
        'm': None,
        'will_clock': {'X': False, 'Y': False, 'Z': False},
        'keystream_bit': X[18] ^ Y[21] ^ Z[22],
        'output_bit': None,
        'keystream_so_far': '',
        'result_so_far': ''
    })

    for i, char_bit in enumerate(input_str):
        bit_in = int(char_bit)

        x8, y10, z10 = X[8], Y[10], Z[10]
        m = maj(x8, y10, z10)

        will_x = (x8 == m)
        will_y = (y10 == m)
        will_z = (z10 == m)

        t_x = X[13] ^ X[16] ^ X[17] ^ X[18]
        t_y = Y[20] ^ Y[21]
        t_z = Z[7] ^ Z[20] ^ Z[21] ^ Z[22]

        if will_x:
            for j in range(18, 0, -1):
                X[j] = X[j - 1]
            X[0] = t_x

        if will_y:
            for j in range(21, 0, -1):
                Y[j] = Y[j - 1]
            Y[0] = t_y

        if will_z:
            for j in range(22, 0, -1):
                Z[j] = Z[j - 1]
            Z[0] = t_z

        s_i = X[18] ^ Y[21] ^ Z[22]
        out_bit = bit_in ^ s_i

        keystream_bits.append(str(s_i))
        result_bits.append(str(out_bit))

        steps.append({
            'step_index': i + 1,
            'input_bit': bit_in,
            'X': list(X),
            'Y': list(Y),
            'Z': list(Z),
            'clock_bits': {'X': x8, 'Y': y10, 'Z': z10},
            'm': m,
            'will_clock': {'X': will_x, 'Y': will_y, 'Z': will_z},
            't_values': {'X': t_x, 'Y': t_y, 'Z': t_z},
            'keystream_bit': s_i,
            'output_bit': out_bit,
            'keystream_so_far': "".join(keystream_bits),
            'result_so_far': "".join(result_bits)
        })

    return {
        'steps': steps,
        'final_keystream': "".join(keystream_bits),
        'final_result': "".join(result_bits)
    }, None

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