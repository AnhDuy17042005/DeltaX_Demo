# Demo Tracking Cap

Hệ thống `pick-and-place nắp chai` dùng `camera`, `robot Delta`, `calibration tọa độ` và hai pipeline thị giác máy tính để phát hiện nắp đang chạy trên băng tải, quy đổi tọa độ ảnh sang mm, bù trễ chuyển động và điều khiển robot gắp theo màu.

## Tính năng chính

- Hiệu chuẩn camera bằng checkerboard và lưu `camera_calib_data.npz`.
- Tính `OFFSET_X`, `OFFSET_Y` để ánh xạ từ hệ tọa độ camera sang robot.
- Hỗ trợ hai pipeline xử lý ảnh:
  - `src/Classic_CV_Tracking.py`: xử lý ảnh cổ điển bằng OpenCV.
  - `src/DL_Tracking.py`: Deep Learning với YOLO + ByteTrack.
- Điều khiển robot Delta bằng G-code qua cổng serial.
- Cung cấp GUI cho các bước scan ảnh, calibration, offset và vận hành hệ thống.

## Chuẩn bị môi trường

### Yêu cầu

- Python và `pip`
- Camera dùng để quan sát vùng làm việc
- Robot Delta kết nối serial nếu chạy phần cứng thật
- Trọng số `runs/detect/train/weights/best.pt` nếu dùng pipeline Deep Learning
- Dataset đã gán nhãn và `data.yaml` nếu muốn train lại mô hình

### Tạo môi trường ảo

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### Cài thư viện

```bash
pip install -r requirements.txt
```

Nếu chạy YOLO bằng GPU, nên cài phiên bản `PyTorch` phù hợp với máy trước khi cài các phụ thuộc còn lại.

## Cách chạy

Entry point thực tế là:

```bash
python GUI/GUI_Tracking.py
```

Các lệnh thường dùng:

| Mục đích | Lệnh |
| --- | --- |
| Chụp và lưu ảnh từ camera | `python GUI/GUI_Scan_Images.py` |
| Calibration camera | `python GUI/GUI_Calibration.py` |
| Tính offset camera -> robot | `python GUI/GUI_Auto_Offset.py` |
| Chạy giao diện điều khiển tổng hợp | `python GUI/GUI_Tracking.py` |
| Chụp ảnh bằng script | `python src/Scan_Images.py` |
| Calibration bằng script | `python src/Calibration.py` |
| Tính offset bằng script | `python src/Auto_Offset.py` |
| Train YOLO | `python src/Train_YOLO.py` |
| Test mô hình YOLO | `python src/Test_Model.py` |
| Chạy pipeline cổ điển | `python src/Classic_CV_Tracking.py` |
| Chạy pipeline Deep Learning | `python src/DL_Tracking.py` |

## Quy trình vận hành đề xuất

1. Thu ảnh checkerboard bằng `GUI/GUI_Scan_Images.py` hoặc `src/Scan_Images.py`.
2. Chạy calibration để tạo `camera_calib_data.npz`.
3. Chạy auto offset để lấy `OFFSET_X`, `OFFSET_Y`.
4. Nếu dùng Deep Learning, chuẩn bị dataset và `data.yaml`, sau đó train/test mô hình.
5. Vận hành hệ thống bằng `GUI/GUI_Tracking.py` hoặc các script trong `src/`.

## Kiến trúc hệ thống

Project tổ chức theo mô hình hai luồng chính:

- `Luồng xử lý ảnh`
  - Đọc frame từ camera
  - Phát hiện hoặc tracking nắp chai
  - Tính tâm vật thể
  - Quy đổi từ pixel sang mm bằng dữ liệu calibration
  - Đưa mục tiêu vào `PriorityQueue`

- `Luồng điều khiển robot Delta`
  - Lấy mục tiêu từ queue
  - Bù trễ theo tốc độ băng tải và độ trễ xử lý
  - Cộng offset để đổi từ hệ camera sang hệ robot
  - Gửi G-code để robot thực hiện pick-and-place

## Hai pipeline xử lý ảnh

### `src/Classic_CV_Tracking.py`

Pipeline OpenCV cổ điển, phù hợp khi ánh sáng ổn định:

- Tách màu trong không gian `HSV`
- Lọc nhiễu bằng morphology
- Tìm contour và kiểm tra hình dạng
- Tính tâm nắp và đổi tọa độ sang mm
- Đưa vật thể hợp lệ vào queue

### `src/DL_Tracking.py`

Pipeline Deep Learning cho môi trường thực tế phức tạp hơn:

- Load YOLO từ `runs/detect/train/weights/best.pt`
- Tracking với ByteTrack qua `model.track(...)`
- Lấy `track_id`, class và tâm bounding box
- Quy đổi tọa độ sang mm
- Xếp hàng mục tiêu để robot gắp theo màu

## Cấu trúc thư mục

```text
Demo_TrackingCap/
|-- ByteTrack/                     # Mã nguồn ByteTrack đi kèm repo
|-- Config/
|   `-- robot_config.json          # Cấu hình robot, camera, offset và timing
|-- GUI/
|   |-- GUI_Auto_Offset.py         # GUI tính offset camera -> robot
|   |-- GUI_Calibration.py         # GUI calibration camera
|   |-- GUI_Scan_Images.py         # GUI chụp và lưu ảnh
|   `-- GUI_Tracking.py            # GUI điều khiển hệ thống tracking + robot
|-- calibration_images/
|   `-- camera_calib_data.npz      # Dữ liệu calibration camera
|-- runs/
|   `-- detect/train/weights/
|       |-- best.pt                # Trọng số tốt nhất sau khi train
|       `-- last.pt                # Trọng số cuối cùng
|-- src/
|   |-- Auto_Offset.py             # Tính offset
|   |-- Calibration.py             # Calibration camera
|   |-- Classic_CV_Tracking.py     # Pipeline xử lý ảnh cổ điển
|   |-- DL_Tracking.py             # Pipeline YOLO + ByteTrack
|   |-- Scan_Images.py             # Chụp và lưu ảnh
|   |-- Test_Model.py              # Kiểm thử mô hình trên video
|   `-- Train_YOLO.py              # Train mô hình YOLO
|-- Videos_test/                   # Video test
|-- build/                         # File build/debug
|-- requirements.txt               # Danh sách thư viện cần cài
|-- yolo11n.pt                     # Trọng số khởi tạo cho bước train
`-- README.md
```

## Thành phần chính

- `GUI/GUI_Tracking.py`: ứng dụng điều khiển tổng hợp, phù hợp nhất để chạy hệ thống.
- `src/Calibration.py` và `GUI/GUI_Calibration.py`: tạo dữ liệu calibration camera.
- `src/Auto_Offset.py` và `GUI/GUI_Auto_Offset.py`: tính offset giữa camera và robot.
- `src/Train_YOLO.py`: train mô hình từ `yolo11n.pt`.
- `src/Test_Model.py`: đánh giá nhanh mô hình trên video mẫu.

## Lưu ý

- Một số script đang dùng đường dẫn tuyệt đối từ máy phát triển. Khi chạy trên máy khác, cần chỉnh lại đường dẫn tới file calibration hoặc video test.
- `src/Train_YOLO.py` yêu cầu `data.yaml`, nhưng file này hiện không có sẵn trong repo.
- `src/Classic_CV_Tracking.py` và `src/DL_Tracking.py` đang để phần mở serial ở trạng thái comment; `GUI/GUI_Tracking.py` là nơi kết nối robot thật rõ ràng nhất.
- Để tránh lỗi config tương đối, nên chạy các lệnh từ thư mục gốc của repo.
