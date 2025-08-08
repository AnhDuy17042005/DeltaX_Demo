import cv2
import os

# Thư mục lưu ảnh
output_dir = './calibration_images'
os.makedirs(output_dir, exist_ok=True)

# # Xoá toàn bộ ảnh cũ
# for file in os.listdir(output_dir):
#     file_path = os.path.join(output_dir, file)
#     if os.path.isfile(file_path) and file_path.endswith('.jpg'):
#         os.remove(file_path)
# print("Đã xoá toàn bộ ảnh cũ.")

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Không mở được camera.")
    exit()

count = 0
print("Nhấn 's' để lưu ảnh, 'q' để thoát.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Không nhận được khung hình từ camera.")
        break

    # Hiển thị khung hình
    cv2.imshow('Live Feed', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('s'):
        # Tạo tên file dạng img_00.jpg, img_01.jpg, …
        filename = os.path.join(output_dir, f'img_{count:02d}.jpg')
        cv2.imwrite(filename, frame)
        print(f'[Saved] {filename}')
        count += 1
    elif key == ord('q'):
        break

# Giải phóng và đóng cửa sổ
cap.release()
cv2.destroyAllWindows()
