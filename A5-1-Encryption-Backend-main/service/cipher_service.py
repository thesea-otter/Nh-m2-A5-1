# -*- coding: utf-8 -*-
"""Encryption-only backend service for full A5/1 and Tiny A5/1.

The service is framework-independent and can be imported by a CLI, Flask,
FastAPI, Django, a desktop application, or automated tests.
"""

from typing import Dict, List

from algorithms.a5_1 import A5_1
from algorithms.a5_1_tiny import A5_1_Tiny
from algorithms.base_cipher import StreamCipherAlgorithm


class UnknownAlgorithmError(KeyError):
    """Raised when a requested algorithm has not been registered."""


class KeyValidationError(ValueError):
    """Raised when a user-provided binary key is invalid."""


class CipherService:
    """Single encryption entry point for all registered A5 variants."""

    def __init__(self) -> None:
        self._algorithms: Dict[str, StreamCipherAlgorithm] = {}
        self.register(A5_1())
        self.register(A5_1_Tiny())

    # ------------------------------------------------------------------
    # Algorithm registry
    # ------------------------------------------------------------------
    def register(self, algorithm: StreamCipherAlgorithm) -> None:
        if not isinstance(algorithm, StreamCipherAlgorithm):
            raise TypeError("algorithm must implement StreamCipherAlgorithm")
        self._algorithms[algorithm.name] = algorithm

    def list_algorithms(self) -> List[str]:
        return sorted(self._algorithms)

    def _get(self, algorithm_name: str) -> StreamCipherAlgorithm:
        try:
            return self._algorithms[algorithm_name]
        except KeyError as exc:
            raise UnknownAlgorithmError(
                f"Unknown algorithm '{algorithm_name}'. "
                f"Available algorithms: {self.list_algorithms()}"
            ) from exc

    def info(self, algorithm_name: str) -> dict:
        algo = self._get(algorithm_name)
        return {
            "name": algo.name,
            "key_bits": algo.key_bits,
            "frame_bits": algo.frame_bits,
            "uses_frame": algo.frame_bits > 0,
        }

    # ------------------------------------------------------------------
    # Low-level byte API
    # ------------------------------------------------------------------
    def keystream_hex(
        self, algorithm_name: str, key: bytes, frame: int, num_bits: int
    ) -> str:
        return self._get(algorithm_name).keystream_bytes(key, frame, num_bits).hex()

    def encrypt(
        self, algorithm_name: str, plaintext: bytes, key: bytes, frame: int = 0
    ) -> bytes:
        return self._get(algorithm_name).encrypt(plaintext, key, frame)

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------
    @staticmethod
    def text_to_utf8_bytes(plaintext: str) -> bytes:
        if not isinstance(plaintext, str):
            raise TypeError("plaintext must be a string")
        return plaintext.encode("utf-8")

    @staticmethod
    def bytes_to_binary(data: bytes) -> str:
        return "".join(format(byte, "08b") for byte in data)

    @classmethod
    def text_to_binary(cls, plaintext: str) -> str:
        return cls.bytes_to_binary(cls.text_to_utf8_bytes(plaintext))

    @staticmethod
    def _validate_binary_string(binary_str: str, *, allow_empty: bool = False) -> str:
        if not isinstance(binary_str, str):
            raise TypeError("Binary input must be a string")

        value = binary_str.strip()
        if not value and not allow_empty:
            raise ValueError("Binary string must not be empty")
        if any(char not in "01" for char in value):
            raise ValueError("Binary string may contain only '0' and '1'")
        return value

    @classmethod
    def binary_to_bytes(cls, binary_str: str) -> bytes:
        """Convert a byte-aligned binary string to bytes (MSB-first)."""
        value = cls._validate_binary_string(binary_str)
        if len(value) % 8 != 0:
            raise ValueError(
                "Binary string length must be a multiple of 8 bits "
                f"(received {len(value)} bits)"
            )
        return bytes(int(value[i : i + 8], 2) for i in range(0, len(value), 8))

    @classmethod
    def _binary_to_left_aligned_bytes(cls, binary_str: str) -> bytes:
        """Pack arbitrary-length bits MSB-first with zero right-padding."""
        value = cls._validate_binary_string(binary_str)
        padding = (-len(value)) % 8
        return cls.binary_to_bytes(value + ("0" * padding))

    # ------------------------------------------------------------------
    # Key handling
    # ------------------------------------------------------------------
    @staticmethod
    def validate_key_binary(key_binary: str, expected_bits: int) -> str:
        if not isinstance(key_binary, str):
            raise KeyValidationError("Key must be supplied as a binary string")

        value = key_binary.strip()
        if len(value) != expected_bits:
            raise KeyValidationError(
                f"Key must contain exactly {expected_bits} bits; "
                f"received {len(value)} bits."
            )

        invalid_chars = sorted({char for char in value if char not in "01"})
        if invalid_chars:
            raise KeyValidationError(
                "Key may contain only '0' and '1'. "
                f"Invalid characters: {invalid_chars}"
            )
        return value

    def key_binary_to_bytes(self, algorithm_name: str, key_binary: str) -> bytes:
        """Validate and pack a textual binary key for the selected algorithm."""
        algo = self._get(algorithm_name)
        validated = self.validate_key_binary(key_binary, expected_bits=algo.key_bits)
        return self._binary_to_left_aligned_bytes(validated)

    # ------------------------------------------------------------------
    # Bit-string encryption API (especially useful for Tiny examples)
    # ------------------------------------------------------------------
    @staticmethod
    def xor_binary(left: str, right: str) -> str:
        if len(left) != len(right):
            raise ValueError("Binary strings must have the same length for XOR")
        if any(char not in "01" for char in left + right):
            raise ValueError("Binary strings may contain only '0' and '1'")
        return "".join("1" if a != b else "0" for a, b in zip(left, right))

    def encrypt_binary(
        self,
        algorithm_name: str,
        plaintext_binary: str,
        key_binary: str,
        frame: int = 0,
    ) -> Dict[str, str]:
        plaintext_binary = self._validate_binary_string(
            plaintext_binary, allow_empty=True
        )
        algo = self._get(algorithm_name)
        key_bytes = self.key_binary_to_bytes(algorithm_name, key_binary)
        keystream_bits = algo.generate_keystream(
            key_bytes, frame, len(plaintext_binary)
        )
        keystream = "".join(str(bit) for bit in keystream_bits)
        ciphertext_binary = self.xor_binary(plaintext_binary, keystream)

        return {
            "algorithm": algorithm_name,
            "frame": str(frame),
            "plaintext_binary": plaintext_binary,
            "keystream": keystream,
            "ciphertext_binary": ciphertext_binary,
        }

    # ------------------------------------------------------------------
    # UTF-8 text encryption API for frontend integration
    # ------------------------------------------------------------------
    def encrypt_text(
        self,
        algorithm_name: str,
        plaintext: str,
        key_binary: str,
        frame: int = 0,
    ) -> Dict[str, str]:
        algo = self._get(algorithm_name)
        key_bytes = self.key_binary_to_bytes(algorithm_name, key_binary)
        plaintext_bytes = self.text_to_utf8_bytes(plaintext)

        # Generate the keystream exactly once for this encryption request.
        ciphertext_bytes, keystream_bits = algo.encrypt_with_keystream(
            plaintext_bytes, key_bytes, frame
        )
        keystream_binary = "".join(str(bit) for bit in keystream_bits)

        return {
            "algorithm": algorithm_name,
            "frame": str(frame),
            "plaintext_binary": self.bytes_to_binary(plaintext_bytes),
            "keystream": keystream_binary,
            "ciphertext_binary": self.bytes_to_binary(ciphertext_bytes),
            "ciphertext_hex": ciphertext_bytes.hex(),
        }
