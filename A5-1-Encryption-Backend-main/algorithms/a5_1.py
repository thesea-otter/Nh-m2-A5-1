# -*- coding: utf-8 -*-
"""
a5_1.py
--------
Cài đặt ĐẦY ĐỦ thuật toán A5/1 (dùng trong mạng GSM để mã hoá thoại) - tự
cài đặt toàn bộ phần lõi (3 thanh ghi dịch phản hồi tuyến tính - LFSR - với
luật clock đa số) hoàn toàn TỪ ĐẦU bằng các phép bit thuần Python.

KHÔNG dùng bất kỳ thư viện mật mã có sẵn nào (không hashlib, không
Crypto.*, không openssl) cho phần lõi. Toàn bộ logic dưới đây do nhóm tự
suy ra từ đặc tả công khai của thuật toán:

    - 3 thanh ghi LFSR: R1 (19 bit), R2 (22 bit), R3 (23 bit).
    - Bit thấp nhất (LSB) của mỗi thanh ghi được đánh số là bit 0.
    - Tap phản hồi của R1: {13, 16, 17, 18}
      Tap phản hồi của R2: {20, 21}
      Tap phản hồi của R3: {7, 20, 21, 22}
    - Bit "clock" (dùng để bầu đa số, quyết định thanh ghi nào được dịch)
      của R1 là bit 8; của R2 và R3 là bit 10.
    - Bit ngõ ra của mỗi thanh ghi là bit cao nhất (MSB) của thanh ghi đó.

Tham khảo đặc tả công khai (không phải thư viện mật mã, chỉ là tài liệu
mô tả thuật toán mà nhóm dùng để tự lập trình lại):
    M. Briceno, I. Goldberg, D. Wagner, "A pedagogical implementation of
    A5/1", 1999 - và bài viết A5/1 trên Wikipedia.

Quy ước tải khoá/số khung và số vòng trộn (64 bit khoá, 22 bit số khung,
100 vòng trộn, sinh 2*114 bit keystream) đúng theo đặc tả gốc dùng trong
GSM.
"""

from typing import List

from .base_cipher import StreamCipherAlgorithm


def _parity(x: int) -> int:
    """Return the parity (XOR of all set bits) of ``x``."""
    return bin(x).count("1") & 1


class A5_1(StreamCipherAlgorithm):
    """Thuật toán A5/1 đầy đủ (64-bit key, 22-bit frame number)."""

    name = "a5/1"
    key_bits = 64
    frame_bits = 22

    # --- Độ dài từng thanh ghi ---
    R1_LEN = 19
    R2_LEN = 22
    R3_LEN = 23

    # --- Mặt nạ (mask) độ dài thanh ghi ---
    R1_MASK = (1 << R1_LEN) - 1   # 0x07FFFF
    R2_MASK = (1 << R2_LEN) - 1   # 0x3FFFFF
    R3_MASK = (1 << R3_LEN) - 1   # 0x7FFFFF

    # --- Bit "clock" (bit giữa) dùng để bầu đa số ---
    R1_CLOCK_BIT = 1 << 8    # bit 8
    R2_CLOCK_BIT = 1 << 10   # bit 10
    R3_CLOCK_BIT = 1 << 10   # bit 10

    # --- Tap phản hồi, ứng với đa thức nguyên thuỷ:
    #     x^19+x^18+x^17+x^14+1 (R1), x^22+x^21+1 (R2),
    #     x^23+x^22+x^21+x^8+1 (R3) ---
    R1_TAPS = (1 << 18) | (1 << 17) | (1 << 16) | (1 << 13)
    R2_TAPS = (1 << 21) | (1 << 20)
    R3_TAPS = (1 << 22) | (1 << 21) | (1 << 20) | (1 << 7)

    # --- Tap lấy ngõ ra: bit cao nhất (MSB) của mỗi thanh ghi ---
    R1_OUT = 1 << 18
    R2_OUT = 1 << 21
    R3_OUT = 1 << 22

    NUM_MIXING_CLOCKS = 100  # số vòng "trộn" sau khi nạp khoá + số khung

    # ------------------------------------------------------------------
    # Các thao tác cấp thấp trên một thanh ghi
    # ------------------------------------------------------------------
    @staticmethod
    def _clock_one(reg: int, mask: int, taps: int) -> int:
        """Dịch MỘT thanh ghi đi 1 bit (không quan tâm luật đa số).

        - Tính bit phản hồi = parity(reg AND taps).
        - Dịch thanh ghi sang trái 1 bit (bit tràn ra ngoài bị bỏ, cắt
          theo `mask` để giữ đúng độ dài thanh ghi).
        - Đưa bit phản hồi vừa tính vào vị trí LSB (bit 0).
        """
        feedback = _parity(reg & taps)
        reg = (reg << 1) & mask
        reg |= feedback
        return reg

    def _majority(self, r1: int, r2: int, r3: int) -> int:
        """Bầu đa số trên 3 bit "clock" của R1, R2, R3."""
        b1 = 1 if (r1 & self.R1_CLOCK_BIT) else 0
        b2 = 1 if (r2 & self.R2_CLOCK_BIT) else 0
        b3 = 1 if (r3 & self.R3_CLOCK_BIT) else 0
        return 1 if (b1 + b2 + b3) >= 2 else 0

    def _clock_majority(self, r1: int, r2: int, r3: int):
        """Dịch các thanh ghi mà bit clock của nó trùng với bit đa số
        (luật "dừng/chạy" đặc trưng của A5/1, tạo tính phi tuyến)."""
        maj = self._majority(r1, r2, r3)
        if ((r1 & self.R1_CLOCK_BIT) != 0) == bool(maj):
            r1 = self._clock_one(r1, self.R1_MASK, self.R1_TAPS)
        if ((r2 & self.R2_CLOCK_BIT) != 0) == bool(maj):
            r2 = self._clock_one(r2, self.R2_MASK, self.R2_TAPS)
        if ((r3 & self.R3_CLOCK_BIT) != 0) == bool(maj):
            r3 = self._clock_one(r3, self.R3_MASK, self.R3_TAPS)
        return r1, r2, r3

    def _output_bit(self, r1: int, r2: int, r3: int) -> int:
        """Bit ngõ ra = XOR của bit cao nhất mỗi thanh ghi."""
        return (
            _parity(r1 & self.R1_OUT)
            ^ _parity(r2 & self.R2_OUT)
            ^ _parity(r3 & self.R3_OUT)
        )

    # ------------------------------------------------------------------
    # Nạp khoá + số khung (key setup)
    # ------------------------------------------------------------------
    def _key_setup(self, key: bytes, frame: int):
        if not isinstance(key, (bytes, bytearray)):
            raise TypeError("A5/1 key must be bytes or bytearray")
        if len(key) * 8 != self.key_bits:
            raise ValueError(
                f"A5/1 requires exactly {self.key_bits} key bits; "
                f"received {len(key) * 8} bits"
            )
        if not isinstance(frame, int) or isinstance(frame, bool):
            raise TypeError("frame must be an integer")
        if not (0 <= frame < (1 << self.frame_bits)):
            raise ValueError(
                f"frame must be in [0, 2^{self.frame_bits})"
            )

        r1 = r2 = r3 = 0

        # Nạp 64 bit khoá: LSB của byte đầu tiên trước, mỗi bit đều dịch
        # cả 3 thanh ghi (KHÔNG áp dụng luật đa số trong giai đoạn này).
        for i in range(self.key_bits):
            r1 = self._clock_one(r1, self.R1_MASK, self.R1_TAPS)
            r2 = self._clock_one(r2, self.R2_MASK, self.R2_TAPS)
            r3 = self._clock_one(r3, self.R3_MASK, self.R3_TAPS)
            key_bit = (key[i // 8] >> (i % 8)) & 1
            r1 ^= key_bit
            r2 ^= key_bit
            r3 ^= key_bit

        # Nạp 22 bit số khung, LSB trước, vẫn chưa bật luật đa số.
        for i in range(self.frame_bits):
            r1 = self._clock_one(r1, self.R1_MASK, self.R1_TAPS)
            r2 = self._clock_one(r2, self.R2_MASK, self.R2_TAPS)
            r3 = self._clock_one(r3, self.R3_MASK, self.R3_TAPS)
            frame_bit = (frame >> i) & 1
            r1 ^= frame_bit
            r2 ^= frame_bit
            r3 ^= frame_bit

        # Chạy 100 vòng trộn với luật đa số đã bật, không lấy ngõ ra.
        for _ in range(self.NUM_MIXING_CLOCKS):
            r1, r2, r3 = self._clock_majority(r1, r2, r3)

        return r1, r2, r3

    # ------------------------------------------------------------------
    # Giao diện chuẩn theo StreamCipherAlgorithm
    # ------------------------------------------------------------------
    def generate_keystream(self, key: bytes, frame: int, num_bits: int) -> List[int]:
        if not isinstance(num_bits, int) or isinstance(num_bits, bool) or num_bits < 0:
            raise ValueError("num_bits must be a non-negative integer")

        r1, r2, r3 = self._key_setup(key, frame)
        bits = []
        for _ in range(num_bits):
            r1, r2, r3 = self._clock_majority(r1, r2, r3)
            bits.append(self._output_bit(r1, r2, r3))
        return bits

    def generate_gsm_burst_keystreams(self, key: bytes, frame: int):
        """Hàm tiện ích riêng của A5/1: sinh đúng 2*114 bit theo đúng quy
        ước GSM gốc - 114 bit đầu cho chiều A->B (downlink), 114 bit sau
        cho chiều B->A (uplink)."""
        bits = self.generate_keystream(key, frame, 228)
        a_to_b = self._bits_to_bytes(bits[:114])
        b_to_a = self._bits_to_bytes(bits[114:])
        return a_to_b, b_to_a
