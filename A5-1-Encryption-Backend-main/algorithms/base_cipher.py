# -*- coding: utf-8 -*-
"""Shared interface for A5-family stream-encryption algorithms.

The concrete algorithms only need to implement ``generate_keystream``.
Encryption is then the XOR of plaintext bytes with that keystream.

This project intentionally exposes only keystream generation and encryption,
matching the assigned backend scope.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple


class StreamCipherAlgorithm(ABC):
    """Common interface implemented by full A5/1 and Tiny A5/1."""

    name: str = "abstract"
    key_bits: int = 0
    frame_bits: int = 0

    @abstractmethod
    def generate_keystream(self, key: bytes, frame: int, num_bits: int) -> List[int]:
        """Return ``num_bits`` keystream bits, each represented by 0 or 1."""
        raise NotImplementedError

    @staticmethod
    def _bits_to_bytes(bits: List[int]) -> bytes:
        """Pack MSB-first bits into bytes, zero-padding the final byte if needed."""
        out = bytearray((len(bits) + 7) // 8)
        for index, bit in enumerate(bits):
            if bit not in (0, 1):
                raise ValueError("Keystream bits must contain only 0 or 1")
            if bit:
                out[index // 8] |= 0x80 >> (index % 8)
        return bytes(out)

    def keystream_bytes(self, key: bytes, frame: int, num_bits: int) -> bytes:
        """Generate a keystream and pack it into MSB-first bytes."""
        return self._bits_to_bytes(self.generate_keystream(key, frame, num_bits))

    def encrypt_with_keystream(
        self, plaintext: bytes, key: bytes, frame: int
    ) -> Tuple[bytes, List[int]]:
        """Encrypt once and return both ciphertext and the generated keystream.

        Returning the keystream together with the ciphertext lets the service
        display/debug it without generating the same stream a second time.
        """
        if not isinstance(plaintext, (bytes, bytearray)):
            raise TypeError("plaintext must be bytes or bytearray")

        plaintext_bytes = bytes(plaintext)
        keystream_bits = self.generate_keystream(
            key, frame, len(plaintext_bytes) * 8
        )
        keystream_bytes = self._bits_to_bytes(keystream_bits)
        ciphertext = bytes(
            plain_byte ^ key_byte
            for plain_byte, key_byte in zip(plaintext_bytes, keystream_bytes)
        )
        return ciphertext, keystream_bits

    def encrypt(self, plaintext: bytes, key: bytes, frame: int) -> bytes:
        """Encrypt plaintext bytes with the generated stream using XOR."""
        ciphertext, _ = self.encrypt_with_keystream(plaintext, key, frame)
        return ciphertext
