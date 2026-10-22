import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from a51_backend import FileCryptoError
from a51_desktop import DesktopFileController


KEYS = {"a51": "1010" * 16, "tiny_a51": "10110101100101001101001"}


class DesktopControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.controller = DesktopFileController()
        self.original = b"\xef\xbb\xbf" + "Xin chào Việt Nam!\r\n\r\n  cuối dòng  \n".encode()
        self.source = self.folder / "tài liệu gốc.txt"
        self.source.write_bytes(self.original)

    def assert_error(self, code, callback):
        with self.assertRaises(FileCryptoError) as raised:
            callback()
        self.assertEqual(raised.exception.code, code)

    def test_full_select_encrypt_save_select_decrypt_save_each_algorithm(self):
        for algorithm, key in KEYS.items():
            with self.subTest(algorithm=algorithm):
                self.controller.select_file(self.source)
                encrypted = self.controller.process_file("encrypt", key, algorithm)
                encrypted_path = self.folder / f"{algorithm}_encrypted.txt"
                self.assertEqual(self.controller.save_result(encrypted_path), encrypted_path)
                self.assertEqual(encrypted_path.read_bytes(), encrypted.data)
                self.controller.select_file(encrypted_path)
                self.assertIsNone(self.controller.result)
                decrypted = self.controller.process_file("decrypt", key, algorithm)
                decrypted_path = self.folder / f"{algorithm}_decrypted.txt"
                self.controller.save_result(decrypted_path)
                self.assertEqual(decrypted.data, self.original)
                self.assertEqual(decrypted_path.read_bytes(), self.original)
                self.assertEqual(self.source.read_bytes(), self.original)

    def test_select_invalid_file_and_missing_file(self):
        self.assert_error("FILE_NOT_FOUND", lambda: self.controller.select_file(self.folder / "missing.txt"))
        bad = self.folder / "a.pdf"
        bad.write_bytes(b"example")
        self.assert_error("INVALID_FILE_TYPE", lambda: self.controller.select_file(bad))

    def test_process_requires_selection(self):
        self.assert_error("MISSING_FILE", lambda: self.controller.process_file("encrypt", KEYS["a51"], "a51"))

    def test_save_requires_current_result(self):
        self.assert_error("NO_RESULT", lambda: self.controller.save_result(self.folder / "out.txt"))

    def test_failed_processing_discards_old_result(self):
        self.controller.select_file(self.source)
        self.controller.process_file("encrypt", KEYS["a51"], "a51")
        self.assert_error("INVALID_KEY", lambda: self.controller.process_file("encrypt", "101", "a51"))
        self.assertIsNone(self.controller.result)
        self.assert_error("NO_RESULT", lambda: self.controller.save_result(self.folder / "out.txt"))

    def test_explicit_parameter_change_can_clear_result(self):
        self.controller.select_file(self.source)
        self.controller.process_file("encrypt", KEYS["a51"], "a51")
        self.controller.clear_result()
        self.assertIsNone(self.controller.result)

    def test_save_keeps_source_unchanged(self):
        self.controller.select_file(self.source)
        self.controller.process_file("encrypt", KEYS["a51"], "a51")
        self.assert_error("SOURCE_OVERWRITE", lambda: self.controller.save_result(self.source))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_save_blocks_alias_of_source(self):
        alias = self.folder / "alias.txt"
        try:
            alias.hardlink_to(self.source)
        except OSError:
            self.skipTest("Filesystem does not support hard links")
        self.controller.select_file(self.source)
        self.controller.process_file("encrypt", KEYS["a51"], "a51")
        self.assert_error("SOURCE_OVERWRITE", lambda: self.controller.save_result(alias))

    def test_saved_extension_must_be_txt(self):
        self.controller.select_file(self.source)
        self.controller.process_file("encrypt", KEYS["a51"], "a51")
        self.assert_error("INVALID_FILE_TYPE", lambda: self.controller.save_result(self.folder / "out.pdf"))
        self.assertFalse((self.folder / "out.pdf").exists())

    def test_atomic_save_does_not_damage_existing_file_on_failure(self):
        target = self.folder / "existing.txt"
        target.write_bytes(b"existing data")
        self.controller.select_file(self.source)
        self.controller.process_file("encrypt", KEYS["a51"], "a51")
        with patch("a51_desktop.controller.os.replace", side_effect=PermissionError("test locked file")):
            with self.assertRaises(PermissionError):
                self.controller.save_result(target)
        self.assertEqual(target.read_bytes(), b"existing data")
        self.assertEqual(list(self.folder.glob(".a51_result_*.tmp")), [])

    def test_existing_destination_can_be_replaced_after_save_dialog(self):
        target = self.folder / "existing.txt"
        target.write_bytes(b"existing data")
        self.controller.select_file(self.source)
        result = self.controller.process_file("encrypt", KEYS["a51"], "a51")
        self.controller.save_result(target)
        self.assertEqual(target.read_bytes(), result.data)

    def test_empty_file_can_be_processed_and_saved(self):
        empty = self.folder / "empty.txt"
        empty.write_bytes(b"")
        self.controller.select_file(empty)
        self.controller.process_file("encrypt", KEYS["a51"], "a51")
        target = self.folder / "empty_encrypted.txt"
        self.controller.save_result(target)
        self.assertEqual(target.read_bytes(), b"")

    def test_source_removed_after_selection_is_reported(self):
        self.controller.select_file(self.source)
        self.source.unlink()
        with self.assertRaises(FileNotFoundError):
            self.controller.process_file("encrypt", KEYS["a51"], "a51")
        self.assertIsNone(self.controller.result)


if __name__ == "__main__":
    unittest.main()
