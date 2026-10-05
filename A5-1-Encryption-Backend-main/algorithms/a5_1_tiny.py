# -*- coding: utf-8 -*-
"""Educational Tiny A5/1 implementation.

This module implements the 23-bit Tiny A5/1 variant commonly used in
introductory cryptography courses:

- X: 6 bits  (x0 .. x5)
- Y: 8 bits  (y0 .. y7)
- Z: 9 bits  (z0 .. z8)
- key K: 23 bits, distributed directly as K = X || Y || Z
- majority clock: maj(x1, y3, z3)
- feedback:
    X: x2 XOR x4 XOR x5
    Y: y6 XOR y7
    Z: z2 XOR z7 XOR z8
- output bit after conditional clocking: x5 XOR y7 XOR z8

Tiny A5/1 is an educational model, not a GSM/3GPP standard. Unlike the
full A5/1 implementation in ``a5_1.py``, this teaching variant has no frame
number and no key/frame mixing stage. To keep one common backend interface,
``frame`` is accepted but must be 0.

Key byte convention
-------------------
The public algorithm interface uses ``bytes``. A 23-bit key is therefore
stored in 3 bytes, MSB-first and LEFT-ALIGNED, with one zero padding bit at
the end. Example:

    10010101001110100110000  ->  10010101 00111010 0110000[0]
                                0x95       0x3A       0x60

``CipherService.key_binary_to_bytes()`` performs this packing automatically.
"""

from typing import List, Tuple

from .base_cipher import StreamCipherAlgorithm


class A5_1_Tiny(StreamCipherAlgorithm):
    """Tiny A5/1 teaching model with a 23-bit key (6/8/9-bit registers)."""

    name = "a5/1-tiny"
    key_bits = 23
    frame_bits = 0  # This Tiny teaching model has no frame number.

    X_LEN = 6
    Y_LEN = 8
    Z_LEN = 9

    KEY_BYTES = 3
    UNUSED_PADDING_BITS = KEY_BYTES * 8 - key_bits  # 1 bit

    @staticmethod
    def _majority(a: int, b: int, c: int) -> int:
        """Return the majority value of three bits."""
        return 1 if (a + b + c) >= 2 else 0

    @staticmethod
    def _rotate_x(x: List[int]) -> List[int]:
        """Clock X according to t = x2 XOR x4 XOR x5."""
        t = x[2] ^ x[4] ^ x[5]
        return [t] + x[:-1]

    @staticmethod
    def _rotate_y(y: List[int]) -> List[int]:
        """Clock Y according to t = y6 XOR y7."""
        t = y[6] ^ y[7]
        return [t] + y[:-1]

    @staticmethod
    def _rotate_z(z: List[int]) -> List[int]:
        """Clock Z according to t = z2 XOR z7 XOR z8."""
        t = z[2] ^ z[7] ^ z[8]
        return [t] + z[:-1]

    @classmethod
    def _unpack_key_bits(cls, key: bytes) -> List[int]:
        """Decode the left-aligned 23-bit key from exactly three bytes."""
        if not isinstance(key, (bytes, bytearray)):
            raise TypeError("A5/1-Tiny key must be bytes or bytearray")
        if len(key) != cls.KEY_BYTES:
            raise ValueError(
                f"A5/1-Tiny needs exactly {cls.key_bits} bits packed in "
                f"{cls.KEY_BYTES} bytes; received {len(key)} bytes"
            )

        # The unused low-order padding bit in the final byte must be zero.
        padding_mask = (1 << cls.UNUSED_PADDING_BITS) - 1
        if key[-1] & padding_mask:
            raise ValueError(
                "Invalid packed 23-bit key: the final padding bit must be 0. "
                "Use CipherService.key_binary_to_bytes() to pack a binary key."
            )

        bits: List[int] = []
        for byte_value in key:
            for bit_index in range(7, -1, -1):
                bits.append((byte_value >> bit_index) & 1)
        return bits[: cls.key_bits]

    def _key_setup(self, key: bytes, frame: int = 0) -> Tuple[List[int], List[int], List[int]]:
        """Distribute K directly into X, Y and Z as K = X || Y || Z."""
        if frame != 0:
            raise ValueError(
                "A5/1-Tiny teaching model does not use a frame number; frame must be 0"
            )

        bits = self._unpack_key_bits(key)
        x = bits[: self.X_LEN]
        y = bits[self.X_LEN : self.X_LEN + self.Y_LEN]
        z = bits[self.X_LEN + self.Y_LEN :]
        return x, y, z

    def _clock_majority(
        self, x: List[int], y: List[int], z: List[int]
    ) -> Tuple[List[int], List[int], List[int]]:
        """Clock only registers whose control bit equals maj(x1, y3, z3)."""
        m = self._majority(x[1], y[3], z[3])

        if x[1] == m:
            x = self._rotate_x(x)
        if y[3] == m:
            y = self._rotate_y(y)
        if z[3] == m:
            z = self._rotate_z(z)

        return x, y, z

    @staticmethod
    def _output_bit(x: List[int], y: List[int], z: List[int]) -> int:
        """Output s_i = x5 XOR y7 XOR z8 after the conditional clock."""
        return x[5] ^ y[7] ^ z[8]

    def generate_keystream(self, key: bytes, frame: int, num_bits: int) -> List[int]:
        """Generate ``num_bits`` Tiny A5/1 keystream bits."""
        if not isinstance(num_bits, int) or isinstance(num_bits, bool) or num_bits < 0:
            raise ValueError("num_bits must be a non-negative integer")

        x, y, z = self._key_setup(key, frame)
        bits: List[int] = []

        for _ in range(num_bits):
            x, y, z = self._clock_majority(x, y, z)
            bits.append(self._output_bit(x, y, z))

        return bits
