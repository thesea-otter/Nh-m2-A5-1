import base64
import contextlib
import importlib
import io
import random
import unittest

from a51_backend import FileCryptoError, FileCryptoService
from a51_backend.cores import a51, tiny_a51

KEYS = {"a51": "1010" * 16, "tiny_a51": "10110101100101001101001"}


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = FileCryptoService()

    def assert_error(self, code, callback):
        with self.assertRaises(FileCryptoError) as raised:
            callback()
        self.assertEqual(raised.exception.code, code)

    def test_roundtrip_vietnamese_bom_crlf_whitespace_and_empty(self):
        samples = [b"", b" ", b"\r\n\n\t  ", "Xin chào Việt Nam!\r\nĐỨC PHÚC\n  cuối  \n".encode(),
                   b"\xef\xbb\xbf" + "Văn bản có BOM\r\n".encode()]
        for algorithm, key in KEYS.items():
            for data in samples:
                with self.subTest(algorithm=algorithm, data=data):
                    enc = self.service.encrypt_file(io.BytesIO(data), "tài liệu.TXT", key, algorithm)
                    dec = self.service.decrypt_file(enc.data, enc.filename, key, algorithm)
                    self.assertEqual(dec.data, data)
                    self.assertEqual(enc.filename, "tài liệu_encrypted.txt")
                    self.assertEqual(dec.filename, "tài liệu_decrypted.txt")
                    self.assertEqual(enc.to_dict()["content"].encode(), enc.data)
                    self.assertEqual(dec.to_dict()["content"].encode(), data)

    def test_random_unicode_roundtrip(self):
        rng = random.Random(5101)
        alphabet = "abcXYZ0123 Tiếng Việt ĐỨC PHÚC\n\r\t🙂"
        for algorithm, key in KEYS.items():
            for _ in range(12):
                data = "".join(rng.choice(alphabet) for _ in range(rng.randrange(250))).encode()
                enc = self.service.encrypt_file(data, "input.txt", key, algorithm)
                self.assertEqual(self.service.decrypt_file(enc.data, enc.filename, key, algorithm).data, data)

    def test_core_compatibility_known_original_samples(self):
        # Các đầu ra được lấy từ chính chương trình gốc trong ZIP nhóm.
        self.assertEqual(a51.ma_hoa("000101001", "1101001010110010101010111111111111111111111111111111111111111111"), "000101010")
        self.assertEqual(tiny_a51.ma_hoa("001", "11010010101100101010100"), "000")

    def test_service_matches_direct_core_for_each_algorithm(self):
        raw = "Xin chào\r\n".encode()
        bits = "".join(f"{b:08b}" for b in raw)
        for algorithm, core in [("a51", a51), ("tiny_a51", tiny_a51)]:
            result = self.service.encrypt_file(raw, "input.txt", KEYS[algorithm], algorithm)
            cipher_bits = "".join(f"{b:08b}" for b in base64.b64decode(result.data))
            self.assertEqual(cipher_bits, core.ma_hoa(bits, KEYS[algorithm]))

    def test_base64_wrapping_and_bom(self):
        data = "Bản mã có ngắt dòng".encode()
        enc = self.service.encrypt_file(data, "input.txt", KEYS["a51"])
        wrapped = b"\xef\xbb\xbf \r\n" + b" \r\n".join(enc.data[i:i + 4] for i in range(0, len(enc.data), 4)) + b"\n"
        self.assertEqual(self.service.decrypt_file(wrapped, "encrypted.txt", KEYS["a51"]).data, data)

    def test_invalid_key(self):
        for key in [None, "", "1" * 63, "1" * 65, "x" * 64, "0 1" * 21 + "0"]:
            self.assert_error("INVALID_KEY", lambda: self.service.encrypt_file(b"hi", "a.txt", key))
        self.assertEqual(self.service.encrypt_file(b"hi", "a.txt", " " + KEYS["a51"] + "\n").data,
                         self.service.encrypt_file(b"hi", "a.txt", KEYS["a51"]).data)

    def test_invalid_filename_type_and_control(self):
        for name in ["a.pdf", "a.txt.exe", ".txt", "a"]:
            self.assert_error("INVALID_FILE_TYPE", lambda: self.service.encrypt_file(b"hi", name, KEYS["a51"]))
        self.assert_error("INVALID_FILENAME", lambda: self.service.encrypt_file(b"hi", "a\n.txt", KEYS["a51"]))

    def test_filename_path_is_removed(self):
        for name in ["../../test.txt", "C:\\fakepath\\test.txt"]:
            self.assertEqual(self.service.encrypt_file(b"hi", name, KEYS["a51"]).filename, "test_encrypted.txt")

    def test_invalid_operation_and_algorithm(self):
        self.assert_error("INVALID_OPERATION", lambda: self.service.process_file(b"", "a.txt", "other", KEYS["a51"]))
        self.assert_error("INVALID_ALGORITHM", lambda: self.service.process_file(b"", "a.txt", "encrypt", KEYS["a51"], "other"))

    def test_invalid_plaintext_encoding(self):
        self.assert_error("INVALID_UTF8", lambda: self.service.encrypt_file(b"\xff\xfe\x00", "a.txt", KEYS["a51"]))

    def test_invalid_base64(self):
        for raw in [b"%%%%", b"a", b"====", "không phải bản mã".encode()]:
            self.assert_error("INVALID_BASE64", lambda: self.service.decrypt_file(raw, "a.txt", KEYS["a51"]))

    def test_invalid_decrypted_utf8(self):
        # Tạo bản mã của byte không phải UTF-8 để kiểm tra lỗi hiển thị.
        cipher = self.service._transform(b"\xff", KEYS["a51"], a51)
        self.assert_error("INVALID_DECRYPTED_UTF8", lambda: self.service.decrypt_file(base64.b64encode(cipher), "a.txt", KEYS["a51"]))

    def test_size_limits_on_bytes_and_streams(self):
        service = FileCryptoService(max_plaintext_bytes=16)
        for upload in [b"x" * 17, io.BytesIO(b"x" * 17)]:
            self.assert_error("FILE_TOO_LARGE", lambda: service.encrypt_file(upload, "a.txt", KEYS["a51"]))
        for upload in [b"x" * 16, io.BytesIO(b"x" * 16)]:
            self.assertEqual(service.encrypt_file(upload, "a.txt", KEYS["a51"]).input_size, 16)
        self.assert_error("FILE_TOO_LARGE", lambda: service.decrypt_file(base64.b64encode(b"a" * 17), "a.txt", KEYS["a51"]))
        self.assert_error("FILE_TOO_LARGE", lambda: service.decrypt_file(b" " * (service.max_ciphertext_bytes + 1), "a.txt", KEYS["a51"]))

    def test_default_maximum_file_roundtrip(self):
        data = b"abc\r\n " * (65536 // 6) + b"a" * (65536 % 6)
        enc = self.service.encrypt_file(data, "max.txt", KEYS["a51"])
        self.assertEqual(self.service.decrypt_file(enc.data, enc.filename, KEYS["a51"]).data, data)

    def test_invalid_upload_and_short_reads(self):
        for upload in ["hi", io.StringIO("hi"), None]:
            self.assert_error("INVALID_UPLOAD", lambda: self.service.encrypt_file(upload, "a.txt", KEYS["a51"]))
        class ShortRead(io.BytesIO):
            def read(self, n=-1):
                return super().read(min(3, n))
        self.assertEqual(self.service.encrypt_file(ShortRead(b"hello world"), "a.txt", KEYS["a51"]).input_size, 11)

    def test_core_imports_have_no_demo_output(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            importlib.reload(a51)
            importlib.reload(tiny_a51)
        self.assertEqual(output.getvalue(), "")

    def test_process_calls_are_independent(self):
        first = self.service.encrypt_file(b"hello", "a.txt", KEYS["a51"])
        self.service.encrypt_file(b"different data", "b.txt", "1" * 64)
        self.assertEqual(first.data, self.service.encrypt_file(b"hello", "a.txt", KEYS["a51"]).data)
