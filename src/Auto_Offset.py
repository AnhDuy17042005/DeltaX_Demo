import cv2
import numpy as np

# Mở camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Không thể mở camera")
    exit()

# Đọc dữ liệu calibration
data = np.load(r"D:\StudyDocuments_at_BKU\Python\DeltaX2_Demo\calibration_images\camera_calib_data.npz")
mtx = data['mtx']
dist = data['dist']

# Thông số nội tại của camera
fx = mtx[0, 0]
fy = mtx[1, 1]
cx = mtx[0, 2]
cy = mtx[1, 2]

Z = 465  # Khoảng cách từ camera đến băng tải

# Tính tỷ lệ chuyển đổi pixel -> mm
mm_per_pixel_x = Z / fx
mm_per_pixel_y = Z / fy

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:

        x_mm = -(x - cx) * mm_per_pixel_x
        y_mm = (y - cy) * mm_per_pixel_y
        print(f"Toạ độ camera: ({x_mm:.2f}, {y_mm:.2f})")

        try:
            # Nhập tọa độ robot tại vị trí đã nhấp
            X_robot = float(input(">> Nhập X robot (G-code): "))
            Y_robot = float(input(">> Nhập Y robot (G-code): "))

            OFFSET_X = X_robot - x_mm
            OFFSET_Y = Y_robot - y_mm

            print(f"\nOFFSET_X = {OFFSET_X:.2f}")
            print(f"OFFSET_Y = {OFFSET_Y:.2f}\n")

        except ValueError:
            print("Nhập sai giá trị!")

cv2.namedWindow("Calibration")
cv2.setMouseCallback("Calibration", mouse_callback)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Không nhận được frame")
        break

    # Hiển thị điểm gốc
    cv2.circle(frame, (int(cx), int(cy)), 4, (0, 255, 255), -1)
    cv2.putText(frame, "Goc (0,0)", (int(cx)+5, int(cy)-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    cv2.imshow("Calibration", frame)
    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
