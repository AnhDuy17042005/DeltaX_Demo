#--------------Test--------------------
import cv2
from ultralytics import YOLO

# Load mô hình đã train
model = YOLO('runs/detect/train/weights/best.pt')

# Đọc video
video_path = r"D:\StudyDocuments_at_BKU\Python\DeltaX2_Demo\Videos_test\YOLO_1.mp4"
cap = cv2.VideoCapture(video_path)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Dự đoán với mô hình YOLOv8
    results = model.predict(frame, imgsz=640, conf=0.25)

    # Vẽ kết quả lên frame
    annotated_frame = results[0].plot()

    # Hiển thị kết quả
    cv2.imshow('YOLOv8 Detection', annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Giải phóng tài nguyên
cap.release()
cv2.destroyAllWindows()