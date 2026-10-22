"""Điều phối chọn, xử lý và lưu file; không phụ thuộc giao diện Tkinter."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from a51_backend import FileCryptoError, FileCryptoResult, FileCryptoService


class DesktopFileController:
    def __init__(self, service: FileCryptoService | None = None):
        self.service = service or FileCryptoService()
        self.input_path: Path | None = None
        self.result: FileCryptoResult | None = None

    def select_file(self, filename: str | Path) -> Path:
        path = Path(filename).expanduser().resolve()
        if not path.is_file():
            raise FileCryptoError("FILE_NOT_FOUND", "Không tìm thấy file đã chọn.")
        if path.suffix.lower() != ".txt":
            raise FileCryptoError("INVALID_FILE_TYPE", "Hãy chọn file có phần mở rộng .txt.")
        self.input_path = path
        self.clear_result()
        return path

    def clear_result(self) -> None:
        self.result = None

    def process_file(self, operation: str, key: str, algorithm: str) -> FileCryptoResult:
        self.clear_result()
        if self.input_path is None:
            raise FileCryptoError("MISSING_FILE", "Hãy chọn một file .txt trước khi xử lý.")
        with self.input_path.open("rb") as uploaded_file:
            result = self.service.process_file(
                uploaded_file, self.input_path.name, operation, key, algorithm
            )
        self.result = result
        return result

    def save_result(self, filename: str | Path) -> Path:
        if self.result is None:
            raise FileCryptoError("NO_RESULT", "Hãy mã hóa hoặc giải mã trước khi lưu kết quả.")
        destination = Path(filename).expanduser().resolve()
        if destination.suffix.lower() != ".txt":
            raise FileCryptoError("INVALID_FILE_TYPE", "Hãy lưu kết quả thành file .txt.")
        if self.input_path is not None:
            same_path = destination == self.input_path.resolve()
            if destination.exists() and self.input_path.exists():
                same_path = same_path or destination.samefile(self.input_path)
            if same_path:
                raise FileCryptoError("SOURCE_OVERWRITE", "Hãy chọn tên hoặc vị trí khác để giữ nguyên file nguồn.")
        # Ghi file tạm cùng thư mục rồi thay thế để tránh lưu dở dang.
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination.parent, prefix=".a51_result_", suffix=".tmp", delete=False
            ) as output:
                temporary_path = Path(output.name)
                output.write(self.result.data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary_path, destination)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        return destination
