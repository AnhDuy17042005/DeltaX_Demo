import cv2
import numpy as np
import serial
import time
import threading
import queue
import math
from ultralytics import YOLO

# Khởi tạo camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# # Khởi tạo kết nối serial
# ser = serial.Serial('COM8', 115200, timeout=1)
# time.sleep(2)

# Hàm gửi lệnh G-code
def send_gcode(cmd, wait = 0.5):
    # ser.write((cmd + '\n').encode('utf-8'))
    time.sleep(wait)

# Gửi lệnh khởi tạo trước khi bắt đầu
send_gcode("G28", wait = 1)
send_gcode("M360 E0", wait = 1)

drop_zones = {
    'white': (100, -60),
    'blue': (100, 6),
    'red':   (100, 70),
}

Z_PICK = -361  # Gắp nắp chai
Z_MOVE = -342  # Di chuyển

# Load mô hình đã train
model = YOLO('runs/detect/train/weights/best.pt')

# Đọc dữ liệu calibration
data = np.load(r"D:\StudyDocuments_at_BKU\Python\DeltaX2_Demo\calibration_images\camera_calib_data.npz")
mtx = data['mtx']
dist = data['dist']

# Lấy thông số từ ma trận camera
fx = mtx[0, 0]  # Tiêu cự theo trục x
fy = mtx[1, 1]  # Tiêu cự theo trục y
cx = mtx[0, 2]  # Tâm ảnh theo trục x
cy = mtx[1, 2]  # Tâm ảnh theo trục y

Z = 465  # Chiều cao camera đến băng tải

# Tính tỷ lệ chuyển đổi pixel sang mm
mm_per_pixel_x = Z / fx
mm_per_pixel_y = Z / fy

# Kiểm tra xem camera có mở được không
if not cap.isOpened():
    print("Không thể mở camera")
    exit()

# Queue cho robot
task_queue = queue.PriorityQueue()
processed_lock = threading.Lock()

# Hằng số bù trừ
DISTANCE_THRESHOLD = 25.0                                 
V_BELT = 80.0                                           # Tốc độ băng tải (mm/s)
PROCESSING_DELAY = 0.42                                 # Thời gian xử lý ảnh
ROBOT_REACTION_DELAY = 0.42                             # Thời gian robot phản ứng
TOTAL_DELAY = PROCESSING_DELAY + ROBOT_REACTION_DELAY   # Tổng thời gian trễ
OFFSET_DELAY = V_BELT / 40                              # Bù trừ tốc độ băng tải

# OFFSET
OFFSET_X = -4
OFFSET_Y = 279

# Cờ kiểm soát detect/gắp
is_picking = False

# Luồng điều khiển robot
def deltaX2_thread():
    global is_picking
    last_detection_time = time.time()
    NO_CAP_TIMEOUT = 15.0  # Thời gian chờ trước khi về home khi không phát hiện nắp
    has_returned_home = False
    
    while True:
        try:
            # Nhận dữ liệu kèm thời điểm phát hiện
            priority, (detection_time, x_mm, y_mm, color_name, tid) = task_queue.get(timeout=1)
            current_time = time.time()
            
            # Tính thời gian trễ thực tế
            total_delay = current_time - detection_time + TOTAL_DELAY 
            
            # Bù trừ tốc độ băng tải
            y_compensated = y_mm - V_BELT * total_delay - OFFSET_DELAY
            
            last_detection_time = current_time

            robot_x = x_mm + OFFSET_X
            robot_y = y_compensated + OFFSET_Y
            
            drop_x, drop_y = drop_zones[color_name]

            print(f"Nắp {color_name} tại ({robot_x:.2f}, {robot_y:.2f}) | Bù trừ: -{V_BELT * total_delay:.2f}mm")
            
            if robot_y > 160 or robot_y < -160:
                print("Toạ độ ngoài phạm vi delta X 2, bỏ qua")
                continue

            is_picking = True

            send_gcode(f"G1 X{robot_x:.2f} Y{robot_y:.2f} Z{Z_MOVE} F600", wait = 0.5)
            send_gcode(f"G1 Z{Z_PICK} F1600", wait = 0)
            send_gcode("M03", wait = 0)
            send_gcode(f"G1 Z{Z_MOVE} F1600", wait = 0.5)
            send_gcode(f"G1 X{drop_x} Y{drop_y} Z{Z_MOVE} F600", wait = 0.5)
            send_gcode("M05", wait = 0.75)

            is_picking = False
            last_detection_time = current_time
            has_returned_home = False

        except queue.Empty:
            # Kiểm tra nếu đã lâu không phát hiện nắp
            if time.time() - last_detection_time > NO_CAP_TIMEOUT and not has_returned_home:
                print("Không phát hiện nắp trong", NO_CAP_TIMEOUT, "giây. Về vị trí home...")
                send_gcode("G28", wait=1)
                has_returned_home = True
            continue

# Khởi động luồng robot
threading.Thread(target=deltaX2_thread, daemon=True).start()

frame_counter = 0

while True:
    frame_counter += 1
    ret, frame = cap.read()
    if not ret:
        print("Không thể nhận frame. Thoát...")
        break
    if is_picking:
        continue

    img_with_boxes = frame.copy()
    frame_detections = []

    # Vùng ROI
    h, w = img_with_boxes.shape[:2]
    x1_roi = int(w * 0.4)
    x2_roi = int(w * 0.6)
    x1_roi_mm = -(x1_roi - cx) * mm_per_pixel_x
    x2_roi_mm = -(x2_roi - cx) * mm_per_pixel_x

    # Tracking với mô hình YOLO11n 
    results = model.track(
        frame,
        imgsz=640,
        conf=0.3,
        persist=True,
        tracker="bytetrack.yaml",
        verbose=False
    )

    if len(results):
        img_with_boxes = results[0].plot()  

        cv2.rectangle(img_with_boxes, (x1_roi + 10, 0), (x2_roi + 10, h), (255, 0, 0), 2)

        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            class_id = int(box.cls[0].cpu().numpy())
            color_name = model.names[class_id]
            confident = float(box.conf[0].cpu().numpy())

            S = (x2 - x1) * (y2 - y1)
            if S < 700:
                print(f"[SKIP] ID={box.id.item() if box.id is not None else 'None'} | Diện tích quá nhỏ: {S:.1f}")
                continue

            if box.id is None:
                continue
            try:
                track_id = int(box.id.item())
            except:
                continue

            center = (int((x1 + x2)/2), int((y1 + y2)/2))

            # Chuyển sang mm
            center_x_mm = -(center[0] - cx) * mm_per_pixel_x
            center_y_mm =  (center[1] - cy) * mm_per_pixel_y

            if center_x_mm < x2_roi_mm or center_x_mm  > x1_roi_mm:
                print("Toạ độ ngoài phạm vi vùng ROI , bỏ qua")
                continue

            frame_detections.append((track_id,center_x_mm, center_y_mm, color_name))

    detection_time = time.time()
    
    # ưu tiên y và enqueue tasks
    for tid, x_mm, y_mm, cname in sorted(frame_detections, key=lambda t: t[2]):
        task_queue.put(((y_mm, frame_counter), (detection_time, x_mm, y_mm, cname, tid)))
        print(f"[QUEUE] ID={tid:>3} | color={cname:<5} | x={x_mm:>6.1f} | y={y_mm:>6.1f}")

    # Hiển thị kết quả
    cv2.imshow("Detected Boxes", img_with_boxes)
    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

# Giải phóng tài nguyên
cap.release()
cv2.destroyAllWindows()
