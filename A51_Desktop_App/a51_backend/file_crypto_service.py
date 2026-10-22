"""Nhận dữ liệu upload, gọi core và chuẩn bị văn bản/file kết quả.

Không phụ thuộc HTTP, Flask, FastAPI hoặc Tkinter. Không lưu file lên đĩa.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import BinaryIO

from .cores import a51, tiny_a51


class FileCryptoError(ValueError):
    """Lỗi đầu vào có mã ổn định để API/giao diện xử lý."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class FileCryptoResult:
    filename: str
    data: bytes
    algorithm: str
    operation: str
    input_size: int
    mime_type: str = "text/plain; charset=utf-8"

    @property
    def content(self) -> str:
        return self.data.decode("utf-8")

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "content": self.content,
            "mime_type": self.mime_type,
            "algorithm": self.algorithm,
            "operation": self.operation,
            "input_size": self.input_size,
            "output_size": len(self.data),
        }


class FileCryptoService:
    """Mã hóa/giải mã TXT UTF-8; bản mã là Base64 ASCII trong file TXT.

    Mỗi lần gọi core tạo lại trạng thái thanh ghi, không chia sẻ trạng thái
    giữa các file. Dùng đúng khóa và thuật toán ban đầu khi giải mã.
    """

    ALGORITHMS = {"a51": (a51, 64), "tiny_a51": (tiny_a51, 23)}

    def __init__(self, max_plaintext_bytes: int = 64 * 1024):
        if not isinstance(max_plaintext_bytes, int) or max_plaintext_bytes <= 0:
            raise ValueError("max_plaintext_bytes phải là số nguyên dương.")
        self.max_plaintext_bytes = max_plaintext_bytes
        # Cho phép Base64 có ngắt dòng, khoảng trắng và BOM từ trình soạn thảo.
        self.max_ciphertext_bytes = 4 * ((max_plaintext_bytes + 2) // 3) + 4096

    def encrypt_file(self, upload: bytes | BinaryIO, filename: str, key: str,
                     algorithm: str = "a51") -> FileCryptoResult:
        return self.process_file(upload, filename, "encrypt", key, algorithm)

    def decrypt_file(self, upload: bytes | BinaryIO, filename: str, key: str,
                     algorithm: str = "a51") -> FileCryptoResult:
        return self.process_file(upload, filename, "decrypt", key, algorithm)

    def process_file(self, upload: bytes | BinaryIO, filename: str,
                     operation: str, key: str, algorithm: str = "a51") -> FileCryptoResult:
        if operation not in ("encrypt", "decrypt"):
            raise FileCryptoError("INVALID_OPERATION", "Chọn encrypt hoặc decrypt.")
        if algorithm not in self.ALGORITHMS:
            raise FileCryptoError("INVALID_ALGORITHM", "Thuật toán phải là a51 hoặc tiny_a51.")
        core, key_length = self.ALGORITHMS[algorithm]
        key = self._validate_key(key, key_length)
        filename = self._validate_filename(filename)
        limit = self.max_plaintext_bytes if operation == "encrypt" else self.max_ciphertext_bytes
        raw = self._read_upload(upload, limit)

        if operation == "encrypt":
            self._require_utf8(raw, "INVALID_UTF8", "File đầu vào phải là văn bản UTF-8.")
            result = base64.b64encode(self._transform(raw, key, core))
            output_name = filename[:-4] + "_encrypted.txt"
        else:
            try:
                ascii_data = raw.decode("utf-8-sig").encode("ascii")
                cipher = base64.b64decode(b"".join(ascii_data.split()), validate=True)
            except (UnicodeError, binascii.Error, ValueError) as exc:
                raise FileCryptoError("INVALID_BASE64", "File giải mã phải chứa bản mã Base64 hợp lệ.") from exc
            if len(cipher) > self.max_plaintext_bytes:
                raise FileCryptoError("FILE_TOO_LARGE", "Dữ liệu sau khi đọc Base64 vượt giới hạn cho phép.")
            result = self._transform(cipher, key, core)
            self._require_utf8(
                result, "INVALID_DECRYPTED_UTF8",
                "Kết quả không phải UTF-8. Hãy kiểm tra khóa, thuật toán và file bản mã.",
            )
            stem = filename[:-4]
            if stem.endswith("_encrypted"):
                stem = stem[:-10]
            output_name = stem + "_decrypted.txt"

        return FileCryptoResult(output_name, result, algorithm, operation, len(raw))

    @staticmethod
    def _validate_key(key: str, length: int) -> str:
        if not isinstance(key, str):
            raise FileCryptoError("INVALID_KEY", "Khóa phải là chuỗi bit.")
        key = key.strip()
        if len(key) != length or any(bit not in "01" for bit in key):
            raise FileCryptoError("INVALID_KEY", f"Khóa phải có đúng {length} ký tự 0 hoặc 1.")
        return key

    @staticmethod
    def _validate_filename(filename: str) -> str:
        if not isinstance(filename, str):
            raise FileCryptoError("INVALID_FILENAME", "Tên file không hợp lệ.")
        filename = filename.replace("\\", "/").rsplit("/", 1)[-1]
        if not filename.lower().endswith(".txt") or not filename[:-4].strip():
            raise FileCryptoError("INVALID_FILE_TYPE", "Chỉ hỗ trợ file có phần mở rộng .txt.")
        if any(ord(c) < 32 or ord(c) == 127 for c in filename):
            raise FileCryptoError("INVALID_FILENAME", "Tên file chứa ký tự không hợp lệ.")
        return filename

    @staticmethod
    def _require_utf8(data: bytes, code: str, message: str) -> None:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise FileCryptoError(code, message) from exc

    @staticmethod
    def _read_upload(upload: bytes | BinaryIO, limit: int) -> bytes:
        if isinstance(upload, bytes):
            data = upload
        elif callable(getattr(upload, "read", None)):
            chunks, count = [], 0
            while count <= limit:
                chunk = upload.read(min(65536, limit + 1 - count))
                if not isinstance(chunk, bytes):
                    raise FileCryptoError("INVALID_UPLOAD", "File phải được đọc ở chế độ nhị phân.")
                if not chunk:
                    break
                chunks.append(chunk)
                count += len(chunk)
            data = b"".join(chunks)
        else:
            raise FileCryptoError("INVALID_UPLOAD", "Cần truyền bytes hoặc file mở ở chế độ rb.")
        if len(data) > limit:
            raise FileCryptoError("FILE_TOO_LARGE", f"File vượt giới hạn {limit} byte cho thao tác này.")
        return data

    @staticmethod
    def _transform(data: bytes, key: str, core) -> bytes:
        # Cùng phép XOR cho hai chiều; toàn bộ dữ liệu là một luồng liên tục.
        bits = "".join(f"{byte:08b}" for byte in data)
        transformed = core.ma_hoa(bits, key)
        return bytes(int(transformed[i:i + 8], 2) for i in range(0, len(transformed), 8))
