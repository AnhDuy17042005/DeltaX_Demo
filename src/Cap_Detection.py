import cv2
import numpy as np
import serial
import time
import threading
import queue
import math

# Khởi tạo camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# # Khởi tạo kết nối serial
# ser = serial.Serial('COM8', 115200, timeout=1)
# time.sleep(2)

# Hàm gửi lệnh G-code
def send_gcode(cmd, wait = 0.5):
    # ser.write((cmd + '\n').encode('utf-8'))
    print(f"G-code: {cmd}")
    time.sleep(wait)

# Gửi lệnh khởi tạo trước khi bắt đầu
send_gcode("G28", wait = 1)
send_gcode("M360 E0", wait = 1)

drop_zones = {
    'white': (110, 0),
    'blue': (150, 0),
    'red':   (110, -40),
}

Z_PICK = -361  # Gắp nắp chai
Z_MOVE = -345  # Di chuyển

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
processed_positions = set()
processed_lock = threading.Lock()

# Thêm hằng số bù trừ
DISTANCE_THRESHOLD = 25.0                                 
V_BELT = 50.0                                           # Tốc độ băng tải (mm/s) 
PROCESSING_DELAY = 0.35                                 # Thời gian xử lý ảnh
ROBOT_REACTION_DELAY = 0.35                             # Thời gian robot phản ứng
TOTAL_DELAY = PROCESSING_DELAY + ROBOT_REACTION_DELAY   # Tổng thời gian trễ

# OFFSET
OFFSET_X = -4
OFFSET_Y = 279

# Cờ kiểm soát detect/gắp
is_picking = False

def deltaX2_thread():
    global is_picking
    last_detection_time = time.time()
    NO_CAP_TIMEOUT = 15.0  # Thời gian chờ trước khi về home khi không phát hiện nắp
    has_returned_home = False
    
    while True:
        try:
            # Nhận dữ liệu kèm thời điểm phát hiện
            prority, (detection_time, x_mm, y_mm, color_name) = task_queue.get(timeout=1)
            current_time = time.time()
            
            # Tính thời gian đã trôi qua
            time_elapsed = current_time - detection_time
            total_delay = time_elapsed + TOTAL_DELAY
            
            # Bù trừ tốc độ băng tải
            y_compensated = y_mm - V_BELT * total_delay
            
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
            send_gcode(f"G1 Z{Z_PICK} F1400", wait = 0)
            send_gcode("M03", wait = 0)
            send_gcode(f"G1 Z{Z_MOVE} F1400", wait = 0.5)
            send_gcode(f"G1 X{drop_x} Y{drop_y} Z{Z_MOVE} F600", wait = 0.5)
            send_gcode("M05", wait = 1)

            with processed_lock:
                processed_positions.clear()
                
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

color_ranges = [
    {
        'name': 'white',
        'lower': np.array([0, 0, 150]),
        'upper': np.array([160, 90, 255]),
        'circle_color': (0, 255, 0)
    },
    {
        'name': 'blue',
        'lower': np.array([90, 100, 80]),
        'upper': np.array([120, 255, 255]),
        'circle_color': (255, 0, 0)
    },
    {
        'name': 'red',
        'lower1': np.array([0, 100, 115]),
        'upper1': np.array([10, 255, 255]),
        'lower2': np.array([160, 100, 140]),
        'upper2': np.array([190, 255, 255]),
        'circle_color': (0, 0, 255)
    },
]

frame_counter = 0

while True:
    frame_counter += 1
    # Ghi nhận thời điểm bắt đầu xử lý frame
    detection_time = time.time()
    
    ret, frame = cap.read()
    if not ret:
        print("Không thể nhận frame. Thoát...")
        break
    if is_picking:
        continue

    # Xử lý ảnh
    img = frame.copy()
    img_blur = cv2.GaussianBlur(img, (3, 3), 1)
    hsv = cv2.cvtColor(img_blur, cv2.COLOR_BGR2HSV)

    # Tạo ảnh kết quả
    img_with_boxes = img.copy()
    
    # Vùng ROI
    h, w = img_with_boxes.shape[:2]
    x1_roi = int(w * 0.4)
    x2_roi = int(w * 0.6)
    x1_roi_mm = -(x1_roi - cx) * mm_per_pixel_x
    x2_roi_mm = -(x2_roi - cx) * mm_per_pixel_x

    frame_detections = []
    
    for color in color_ranges:
        if color['name'] == 'red':
            mask1 = cv2.inRange(hsv, color['lower1'], color['upper1'])
            mask2 = cv2.inRange(hsv, color['lower2'], color['upper2'])
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            mask = cv2.inRange(hsv, color['lower'], color['upper'])

        # Lọc nhiễu
        kernel_big = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (1, 1))
        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))        
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_big, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_small, iterations=2)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        cv2.rectangle(img_with_boxes, (x1_roi + 10, 0), (x2_roi + 10, h), (255, 0, 0), 2)

        # Tìm contours trên mask hiện tại
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            # Tính toán các đặc trưng hình dạng
            area = cv2.contourArea(cnt)
            if area < 350:  # Bỏ qua vật quá nhỏ
                continue
                
            # Tính độ tròn (circularity)
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0:
                continue

            circularity = 4 * np.pi * area / (perimeter * perimeter)
            if circularity <= 0.85:
                continue
            
            # Tính tỉ lệ khung hình
            (x, y, w, h) = cv2.boundingRect(cnt)
            aspect_ratio = w / float(h)
            if not (0.4 < aspect_ratio < 1.5):
                continue
            
            # Kiểm tra nếu là hình tròn
            if circularity > 0.85 and 0.4 < aspect_ratio < 1.5:
                # Vẽ kết quả với màu tương ứng
                center = (int(x + w/2), int(y + h/2))
                radius = int(0.5 * max(w, h))

                # Chuyển sang mm
                center_x_mm = -(center[0] - cx) * mm_per_pixel_x
                center_y_mm = (center[1] - cy) * mm_per_pixel_y

                cv2.rectangle(img_with_boxes, (x, y), (x + w, y + h), color['circle_color'], 2)
                cv2.circle(img_with_boxes, center, 4, (0, 0, 0), -1)

                cx_int = int(cx)
                cy_int = int(cy)
                
                # Vẽ điểm gốc tọa độ (màu vàng)
                cv2.circle(img_with_boxes, (cx_int, cy_int), 4, (0, 255, 255), -1)

                # Vẽ text tọa độ
                text = f"({center_x_mm:.2f}, {center_y_mm:.2f})"
                text_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                text_x = x + int((w - text_size[0]) / 2)
                text_y = y - 5 if y > 12 else y + 12
                cv2.putText(img_with_boxes, text, (text_x, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color['circle_color'], 1)
                
                if center_x_mm < x2_roi_mm or center_x_mm  > x1_roi_mm:
                    print("Toạ độ ngoài phạm vi vùng ROI , bỏ qua")
                    continue

                # Lưu thông tin vào danh sách detections
                frame_detections.append((center_x_mm, center_y_mm, color['name']))


    if frame_detections:
        frame_detections.sort(key=lambda item: item[1])  # Ưu tiên nắp gần robot hơn
        for cx_mm, cy_mm, cname in frame_detections:
            with processed_lock:
                if not any(math.hypot(cx_mm - p[0], cy_mm - p[1]) < DISTANCE_THRESHOLD for p in processed_positions):
                    task_queue.put(((cy_mm, frame_counter), (detection_time, cx_mm, cy_mm, cname)))
                    processed_positions.add((cx_mm, cy_mm))
                    print(f"[DEBOUNCE] Đã thêm nắp mới: ({cx_mm:.2f}, {cy_mm:.2f})")

    # Hiển thị kết quả
    cv2.imshow("Detected Boxes", img_with_boxes)   
    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

# Giải phóng tài nguyên
cap.release()
cv2.destroyAllWindows()