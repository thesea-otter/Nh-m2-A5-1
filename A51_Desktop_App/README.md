# Ứng dụng desktop A5/1 — Mã hóa và giải mã file TXT

Ứng dụng mở một **cửa sổ riêng bằng Tkinter**, xử lý file trực tiếp trên máy.
Ứng dụng gọi service Python trực tiếp, hoạt động offline và không khởi chạy
server HTTP. Đây là gói mã nguồn desktop Python, chưa phải file thực thi `.exe`.

## Cách chạy trên Windows

1. Cài **Python 3.10 trở lên có Tcl/Tk**. Nếu đã có Python, có thể kiểm tra
   thành phần này bằng `py -3 -m tkinter`; một cửa sổ kiểm tra sẽ hiện ra.
2. Giải nén toàn bộ ZIP.
3. Mở thư mục đã giải nén và nhấp đúp **`start_windows.bat`**.
4. Cửa sổ ứng dụng xuất hiện. Chọn chức năng, thuật toán, file và nhập khóa.
5. Bấm **Mã hóa file** hoặc **Giải mã file**.
6. Xem toàn bộ kết quả trong cửa sổ rồi bấm **Lưu kết quả thành .txt…** để
   chọn tên file và nơi lưu.

Không cần cài thêm gói Python. Phải giữ nguyên cấu trúc thư mục khi giải nén.
Nếu `.bat` báo thiếu Tcl/Tk, sửa cài đặt Python và bật thành phần Tcl/Tk.

Có thể chạy từ CMD/Terminal:

```bash
python run_desktop.py
```

Hoặc `py -3 run_desktop.py` trên Windows.

Sau khi xác nhận ứng dụng chạy được bằng `.bat`, có thể mở `Mo_ung_dung.pyw`
để chạy qua Python không kèm cửa sổ console, nếu Windows đã liên kết `.pyw`
với Python. Trên macOS/Linux, dùng `python3 run_desktop.py` trong môi trường
desktop có Tkinter.

## Chức năng

| Chức năng | Cách hoạt động |
| --- | --- |
| Chọn file | Hộp thoại chọn file `.txt` trên máy |
| Mã hóa | Đọc UTF-8 → core → Base64 để xem và lưu trong `.txt` |
| Giải mã | Đọc Base64 → core → khôi phục nội dung UTF-8 |
| Tạo khóa | Sinh chuỗi bit theo thuật toán đang chọn; người dùng giữ khóa để giải mã |
| Xem kết quả | Hiển thị toàn bộ nội dung trong vùng văn bản có thanh cuộn |
| Lưu kết quả | Lưu đúng byte đã xử lý, không chạy lại thuật toán khi lưu |
| Sao chép | Sao chép nội dung kết quả vào clipboard khi bấm nút |

- **A5/1 bản nhóm:** khóa 64 ký tự `0` hoặc `1`.
- **Tiny A5/1:** khóa 23 ký tự `0` hoặc `1`.
- Mã hóa file UTF-8 tối đa **65.536 byte (64 KiB)**; hỗ trợ file rỗng.
- Giải mã bằng đúng khóa, thuật toán và core đã dùng để mã hóa.
- Giữ nguyên byte của dấu tiếng Việt, BOM, tab, khoảng trắng và xuống dòng.
- Khi thay file/khóa/thuật toán/chức năng, kết quả cũ được bỏ để tránh lưu nhầm.
- Tác vụ mã hóa/giải mã chạy ở worker thread; giao diện nhận kết quả qua queue.
- Ứng dụng không tự lưu file hay khóa; chỉ ghi kết quả khi người dùng chọn lưu.
- Hộp thoại lưu hỏi trước khi ghi đè file có sẵn. Ứng dụng yêu cầu tên hoặc
  vị trí khác với file nguồn để giữ nguyên dữ liệu đầu vào.

## Cấu trúc mã nguồn

| File/thư mục | Vai trò |
| --- | --- |
| `run_desktop.py` | Điểm khởi chạy cửa sổ |
| `a51_desktop/app.py` | Giao diện Tkinter, hộp thoại, worker và hiển thị |
| `a51_desktop/controller.py` | Mở file nhị phân, gọi service và lưu kết quả |
| `a51_backend/file_crypto_service.py` | Service chung cho mã hóa/giải mã |
| `a51_backend/cores/` | Hai core mô phỏng tách khỏi giao diện |
| `tests/` | Kiểm tra service và luồng chọn/xử lý/lưu file |
| `examples/tieng_viet.txt` | File mẫu để thử |

Giao diện không chứa thuật toán mã hóa. Service có thể được dùng độc lập:

```python
from a51_backend import FileCryptoService

service = FileCryptoService()
with open("examples/tieng_viet.txt", "rb") as file:
    result = service.encrypt_file(file, "tieng_viet.txt", "1010" * 16, "a51")

print(result.content)  # Base64 để hiển thị
# result.data là bytes dùng để lưu file kết quả.
```

## Tương thích và giới hạn của core

Service và hai core giữ nguyên hành vi của gói trước. File Base64 tạo từ gói
trước vẫn có thể giải mã bằng ứng dụng desktop khi dùng đúng khóa/thuật toán.

Core 64 bit là bản mô phỏng của nhóm, **chưa phải triển khai GSM A5/1 đầy đủ**.
Lần chuyển giao diện này không sửa thuật toán, thêm frame hoặc thay đổi cách
sinh khóa dòng. Base64 chỉ biểu diễn bản mã thành văn bản.

File bản mã không chứa khóa, thông tin thuật toán hay xác thực tính toàn vẹn.
Khóa sai/file bị sửa có thể gây lỗi UTF-8 hoặc tạo ra văn bản khác mà không
được phát hiện; thông báo xử lý thành công không xác nhận khóa chắc chắn đúng.

## Đưa mã nguồn lên GitHub

Giải nén rồi đưa `a51_backend/`, `a51_desktop/`, `tests/`, `examples/`,
`run_desktop.py`, `Mo_ung_dung.pyw` và `start_windows.bat` vào thư mục gốc
repository. Nếu đã có README, có thể lưu hướng dẫn này thành
`HUONG_DAN_DESKTOP.md` và gộp các dòng `.gitignore` cần thiết.

Nếu đang dùng gói web cũ, `start_windows.bat` mới sẽ chạy desktop. Các file
web cũ không được dùng bởi chương trình desktop và có thể giữ lại khi cần.
Đưa file đã giải nén vào repository rồi commit để mã nguồn hiện thành các file
Python; tải riêng ZIP lên GitHub chỉ lưu một bản nén.

## Kiểm tra

```bash
python -m unittest discover -s tests -v
```

Các kiểm tra không cần Tkinter hoặc màn hình: khôi phục UTF-8/BOM/CRLF,
Base64, giới hạn dung lượng, mở file, lưu kết quả đúng byte, giữ file nguồn
và không làm hỏng file đích khi quá trình lưu thất bại.

Giao diện Tkinter cần kiểm tra trực tiếp trên máy có desktop/Tcl-Tk hoạt động.
