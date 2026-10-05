# -*- coding: utf-8 -*-
"""Encryption-focused regression, known-answer and backend tests."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from algorithms.a5_1 import A5_1
from algorithms.a5_1_tiny import A5_1_Tiny
from service.cipher_service import CipherService, KeyValidationError, UnknownAlgorithmError


class TestA51Full(unittest.TestCase):
    """Tests for full A5/1 (64-bit key, 22-bit frame)."""

    def setUp(self):
        self.cipher = A5_1()
        self.key = bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88])
        self.frame = 12345

    def test_encrypt_changes_nonempty_plaintext(self):
        plaintext = "Xin chào môn mật mã học!".encode("utf-8")
        ciphertext = self.cipher.encrypt(plaintext, self.key, self.frame)
        self.assertEqual(len(ciphertext), len(plaintext))
        self.assertNotEqual(ciphertext, plaintext)

    def test_keystream_is_deterministic(self):
        self.assertEqual(
            self.cipher.keystream_bytes(self.key, self.frame, 114),
            self.cipher.keystream_bytes(self.key, self.frame, 114),
        )

    def test_frame_changes_keystream(self):
        self.assertNotEqual(
            self.cipher.keystream_bytes(self.key, 1, 114),
            self.cipher.keystream_bytes(self.key, 2, 114),
        )

    def test_known_answer_vector_briceno_1999(self):
        key = bytes([0x12, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF])
        frame = 0x134
        expected_a_to_b = bytes.fromhex("534EAA582FE8151AB6E1855A728C00")
        expected_b_to_a = bytes.fromhex("24FD35A35D5FB6526D32F906DF1AC0")

        a_to_b, b_to_a = self.cipher.generate_gsm_burst_keystreams(key, frame)

        self.assertEqual(a_to_b, expected_a_to_b)
        self.assertEqual(b_to_a, expected_b_to_a)

    def test_known_answer_encryption_first_112_bits(self):
        key = bytes([0x12, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF])
        frame = 0x134
        plaintext = bytes(14)  # 112 zero bits -> ciphertext equals keystream
        expected = bytes.fromhex("534EAA582FE8151AB6E1855A728C")
        self.assertEqual(self.cipher.encrypt(plaintext, key, frame), expected)

    def test_invalid_frame_is_rejected(self):
        with self.assertRaises(ValueError):
            self.cipher.generate_keystream(self.key, 1 << 22, 8)

    def test_key_must_be_exactly_64_bits(self):
        with self.assertRaises(ValueError):
            self.cipher.generate_keystream(self.key + b"\x00", self.frame, 8)
        with self.assertRaises(ValueError):
            self.cipher.generate_keystream(self.key[:-1], self.frame, 8)

    def test_negative_num_bits_is_rejected(self):
        with self.assertRaises(ValueError):
            self.cipher.generate_keystream(self.key, self.frame, -1)


class TestA51Tiny(unittest.TestCase):
    """Tests for the 23-bit educational Tiny A5/1 (X/Y/Z = 6/8/9)."""

    KEY_BINARY = "10010101001110100110000"
    KEY_BYTES = bytes.fromhex("953a60")

    def setUp(self):
        self.cipher = A5_1_Tiny()

    def test_parameters_match_course_variant(self):
        self.assertEqual(self.cipher.key_bits, 23)
        self.assertEqual(self.cipher.X_LEN, 6)
        self.assertEqual(self.cipher.Y_LEN, 8)
        self.assertEqual(self.cipher.Z_LEN, 9)
        self.assertEqual(self.cipher.frame_bits, 0)

    def test_key_is_distributed_directly_to_xyz(self):
        x, y, z = self.cipher._key_setup(self.KEY_BYTES, 0)
        self.assertEqual("".join(map(str, x)), "100101")
        self.assertEqual("".join(map(str, y)), "01001110")
        self.assertEqual("".join(map(str, z)), "100110000")

    def test_course_known_example_first_three_keystream_bits(self):
        self.assertEqual(
            self.cipher.generate_keystream(self.KEY_BYTES, 0, 3), [1, 0, 0]
        )

    def test_course_known_example_encrypts_111_to_011(self):
        plaintext = "111"
        keystream = "".join(
            map(str, self.cipher.generate_keystream(self.KEY_BYTES, 0, 3))
        )
        ciphertext = "".join(
            "1" if plain != key_bit else "0"
            for plain, key_bit in zip(plaintext, keystream)
        )
        self.assertEqual(keystream, "100")
        self.assertEqual(ciphertext, "011")

    def test_rotation_rules_match_course_example(self):
        x = [int(c) for c in "100101"]
        y = [int(c) for c in "01001110"]
        z = [int(c) for c in "100110000"]
        self.assertEqual("".join(map(str, self.cipher._rotate_x(x))), "110010")
        self.assertEqual("".join(map(str, self.cipher._rotate_y(y))), "10100111")
        self.assertEqual("".join(map(str, self.cipher._rotate_z(z))), "010011000")

    def test_known_answer_encryption_first_16_bits(self):
        self.assertEqual(
            self.cipher.encrypt(b"\x00\x00", self.KEY_BYTES, 0),
            bytes.fromhex("9742"),
        )

    def test_keystream_is_deterministic(self):
        self.assertEqual(
            self.cipher.generate_keystream(self.KEY_BYTES, 0, 64),
            self.cipher.generate_keystream(self.KEY_BYTES, 0, 64),
        )

    def test_nonzero_frame_is_rejected(self):
        with self.assertRaises(ValueError):
            self.cipher.generate_keystream(self.KEY_BYTES, 1, 8)

    def test_nonzero_padding_bit_is_rejected(self):
        with self.assertRaises(ValueError):
            self.cipher.generate_keystream(bytes.fromhex("953a61"), 0, 8)


class TestCipherService(unittest.TestCase):
    """End-to-end encryption tests through the public service API."""

    FULL_KEY = "0001000100100010001100110100010001010101011001100111011110001000"
    BRICENO_KEY = "0001001000100011010001010110011110001001101010111100110111101111"
    TINY_KEY = "10010101001110100110000"

    def setUp(self):
        self.service = CipherService()

    def test_algorithms_are_registered(self):
        self.assertEqual(self.service.list_algorithms(), ["a5/1", "a5/1-tiny"])

    def test_info_exposes_frame_usage(self):
        self.assertTrue(self.service.info("a5/1")["uses_frame"])
        self.assertFalse(self.service.info("a5/1-tiny")["uses_frame"])

    def test_tiny_23_bit_key_packing(self):
        packed = self.service.key_binary_to_bytes("a5/1-tiny", self.TINY_KEY)
        self.assertEqual(packed, bytes.fromhex("953a60"))

    def test_tiny_binary_course_example_end_to_end(self):
        result = self.service.encrypt_binary("a5/1-tiny", "111", self.TINY_KEY)
        self.assertEqual(result["keystream"], "100")
        self.assertEqual(result["ciphertext_binary"], "011")

    def test_full_binary_known_answer_end_to_end(self):
        result = self.service.encrypt_binary(
            "a5/1", "0" * 112, self.BRICENO_KEY, frame=0x134
        )
        expected = bin(int("534EAA582FE8151AB6E1855A728C", 16))[2:].zfill(112)
        self.assertEqual(result["keystream"], expected)
        self.assertEqual(result["ciphertext_binary"], expected)

    def test_tiny_text_encryption_output_is_consistent(self):
        plaintext = "Xin chào Tiny A5/1 👋"
        result = self.service.encrypt_text("a5/1-tiny", plaintext, self.TINY_KEY)
        self.assertEqual(
            len(result["keystream"]), len(plaintext.encode("utf-8")) * 8
        )
        self.assertEqual(
            result["ciphertext_binary"],
            self.service.bytes_to_binary(bytes.fromhex(result["ciphertext_hex"])),
        )

    def test_full_text_encryption_output_is_consistent(self):
        plaintext = "Backend A5/1 chuẩn"
        result = self.service.encrypt_text("a5/1", plaintext, self.FULL_KEY, frame=7)
        self.assertEqual(
            len(result["keystream"]), len(plaintext.encode("utf-8")) * 8
        )
        self.assertEqual(
            result["ciphertext_binary"],
            self.service.bytes_to_binary(bytes.fromhex(result["ciphertext_hex"])),
        )

    def test_wrong_key_length_is_rejected(self):
        with self.assertRaises(KeyValidationError):
            self.service.key_binary_to_bytes("a5/1-tiny", "0" * 22)
        with self.assertRaises(KeyValidationError):
            self.service.key_binary_to_bytes("a5/1", "0" * 63)

    def test_non_binary_key_is_rejected(self):
        with self.assertRaises(KeyValidationError):
            self.service.key_binary_to_bytes("a5/1-tiny", "1" * 22 + "x")

    def test_unknown_algorithm_is_rejected(self):
        with self.assertRaises(UnknownAlgorithmError):
            self.service.info("not-an-algorithm")


if __name__ == "__main__":
    unittest.main(verbosity=2)
