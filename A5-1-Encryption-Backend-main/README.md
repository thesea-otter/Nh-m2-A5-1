# A5/1 & Tiny A5/1 Encryption Backend — Python

Python backend tự cài đặt **A5/1 đầy đủ** và **Tiny A5/1 23-bit** cho mục đích học tập, tập trung đúng phạm vi **mã hóa (encryption)**.

> **Security notice:** A5/1 là thuật toán cũ và Tiny A5/1 là mô hình giảng dạy. Không dùng repository này để bảo vệ dữ liệu production.

## 1. Phạm vi project

Backend cung cấp:

- sinh keystream;
- mã hóa dữ liệu bit;
- mã hóa `bytes`;
- mã hóa UTF-8 text;
- validation key / frame / input;
- test vector cho cả A5/1 đầy đủ và Tiny A5/1.

Project không phụ thuộc framework web, nên có thể import vào Flask, FastAPI, Django, CLI hoặc frontend/desktop app khác.

## 2. A5/1 đầy đủ

- Key: **64 bit, bắt buộc đúng 64 bit**
- Frame number: **22 bit**
- R1 / R2 / R3: **19 / 22 / 23 bit**
- Majority clocking: R1 bit 8, R2 bit 10, R3 bit 10
- Feedback taps:
  - R1: `{13, 16, 17, 18}`
  - R2: `{20, 21}`
  - R3: `{7, 20, 21, 22}`
- 100 mixing clocks sau khi nạp key và frame
- Có known-answer test dựa trên implementation sư phạm của Briceno, Goldberg & Wagner (1999)

## 3. Tiny A5/1 (theo trên lớp)

- Key: **23 bit**
- `X`: **6 bit** (`x0..x5`)
- `Y`: **8 bit** (`y0..y7`)
- `Z`: **9 bit** (`z0..z8`)
- Key được phân bố trực tiếp: `K = X || Y || Z`
- Feedback:
  - `X`: `x2 XOR x4 XOR x5`
  - `Y`: `y6 XOR y7`
  - `Z`: `z2 XOR z7 XOR z8`
- Majority control: `maj(x1, y3, z3)`
- Output sau conditional clock: `x5 XOR y7 XOR z8`
- Không dùng frame number; interface yêu cầu `frame=0`

Known example:

```text
K = 100101.01001110.100110000
P = 111
S = 100
C = P XOR S = 011
```

## 4. Cấu trúc

```text
a5_project/
├── algorithms/
│   ├── __init__.py
│   ├── base_cipher.py
│   ├── a5_1.py
│   └── a5_1_tiny.py
├── service/
│   ├── __init__.py
│   └── cipher_service.py
├── tests/
│   ├── __init__.py
│   └── test_suite.py
├── .github/workflows/tests.yml
├── demo.py
├── pyproject.toml
├── requirements.txt
├── SECURITY.md
├── .gitignore
└── README.md
```

## 5. Yêu cầu môi trường

- Python **3.9+**
- Không cần thư viện mật mã bên thứ ba
- Runtime chỉ dùng Python Standard Library

Chạy trực tiếp từ thư mục project hoặc cài editable:

```bash
python -m pip install -e .
```

## 6. Chạy demo encryption

Tiny A5/1:

```bash
python demo.py --algorithm a5/1-tiny --plaintext "Xin chào Tiny"
```

A5/1 đầy đủ:

```bash
python demo.py --algorithm a5/1 --frame 7 --plaintext "Xin chào A5/1"
```

Key Tiny tùy chọn:

```bash
python demo.py \
  --algorithm a5/1-tiny \
  --key 10010101001110100110000 \
  --plaintext "Hello"
```

Output gồm:

```text
algorithm
frame
plaintext_binary
keystream
ciphertext_binary
ciphertext_hex
```

## 7. Dùng `CipherService`

### Tiny A5/1 — text

```python
from service.cipher_service import CipherService

service = CipherService()

result = service.encrypt_text(
    "a5/1-tiny",
    plaintext="Xin chào",
    key_binary="10010101001110100110000",
)

print(result["keystream"])
print(result["ciphertext_binary"])
print(result["ciphertext_hex"])
```

### Tiny A5/1 — bit string

```python
result = service.encrypt_binary(
    "a5/1-tiny",
    plaintext_binary="111",
    key_binary="10010101001110100110000",
)

assert result["keystream"] == "100"
assert result["ciphertext_binary"] == "011"
```

### A5/1 đầy đủ

```python
key = "0001000100100010001100110100010001010101011001100111011110001000"

result = service.encrypt_text(
    "a5/1",
    plaintext="Hello A5/1",
    key_binary=key,
    frame=7,
)
```

## 8. Key Tiny 23-bit trong interface `bytes`

Lớp thuật toán nhận `bytes`, nên 23-bit key được đóng gói MSB-first vào 3 byte và thêm **1 zero padding bit ở bên phải**:

```text
10010101001110100110000
↓
10010101 00111010 01100000
↓
0x95 0x3A 0x60
```

Padding bit không thuộc key. `CipherService.key_binary_to_bytes()` xử lý tự động.

## 9. Chạy test

```bash
python -m unittest discover -s tests -v
```

Test suite bao gồm:

- known-answer keystream A5/1 đầy đủ;
- known-answer encryption A5/1 đầy đủ;
- frame ảnh hưởng keystream;
- key A5/1 phải đúng 64 bit;
- Tiny đúng key 23 bit và X/Y/Z = 6/8/9;
- feedback / rotate / majority theo mô hình Tiny;
- known example Tiny `111 XOR 100 = 011`;
- known-answer Tiny byte encryption;
- validation key, frame và algorithm name;
- end-to-end encryption ở tầng `CipherService`.

GitHub Actions tự chạy cùng bộ test trên Python 3.9, 3.11 và 3.13 khi push hoặc mở pull request.

## 10. Tối ưu thiết kế

- Hai thuật toán dùng chung `StreamCipherAlgorithm` nhưng giữ logic lõi độc lập.
- `CipherService` là entry point duy nhất cho tầng ứng dụng.
- `encrypt_text()` chỉ sinh keystream **một lần** rồi dùng chính stream đó để tạo ciphertext và trả dữ liệu debug.
- A5/1 kiểm tra key đúng **chính xác 64 bit**, tránh việc âm thầm bỏ qua bit dư.
- Tiny kiểm tra bit padding khi đóng gói key 23 bit.
- Không sử dụng thư viện crypto có sẵn cho phần thuật toán.

## 11. Tài liệu tham khảo

- Marc Briceno, Ian Goldberg, David Wagner (1999), *A pedagogical implementation of A5/1*.
- Bài giảng môn học: Tiny A5/1 với key 23 bit và X/Y/Z = 6/8/9 bit.

---

**Project status:** encryption-only final backend build.
