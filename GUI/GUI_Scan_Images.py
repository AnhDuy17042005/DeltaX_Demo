import sys
import os
import cv2
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFileDialog
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer


class CameraApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Camera Capture - PyQt5")
        self.output_dir = os.path.abspath("./calibration_images")
        self.count = 0
        self.cap = None

        # --- Camera preview ---
        self.label_camera = QLabel()
        self.label_camera.setFixedSize(640, 480)

        # --- Info + Buttons ---
        self.label_info = QLabel(f"Images Folder:\n{self.output_dir}")
        self.btn_select_dir = QPushButton("Select Folder")
        self.btn_clear = QPushButton("Delete All Images")
        self.btn_save = QPushButton("Save")
        self.btn_stop = QPushButton("Stop")

        # Right panel layout
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.label_info)
        right_layout.addSpacing(10)
        right_layout.addWidget(self.btn_select_dir)
        right_layout.addWidget(self.btn_clear)
        right_layout.addWidget(self.btn_save)
        right_layout.addWidget(self.btn_stop)
        right_layout.addStretch()

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.label_camera)
        main_layout.addLayout(right_layout)
        self.setLayout(main_layout)

        # --- Events ---
        self.btn_select_dir.clicked.connect(self.select_directory)
        self.btn_clear.clicked.connect(self.clear_images)
        self.btn_save.clicked.connect(self.save_image)
        self.btn_stop.clicked.connect(self.close_app)

        # --- Init camera ---
        self.init_camera()

        # --- Timer update frame ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def init_camera(self):
        os.makedirs(self.output_dir, exist_ok=True)
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Không mở được camera.")
            sys.exit(1)

        self.count = len([f for f in os.listdir(self.output_dir) if f.lower().endswith(".jpg")])

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        self.current_frame = frame
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.label_camera.setPixmap(QPixmap.fromImage(qt_image))

    def select_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu ảnh", self.output_dir)
        if folder:
            self.output_dir = folder
            self.label_info.setText(f"Thư mục lưu ảnh:\n{self.output_dir}")
            os.makedirs(self.output_dir, exist_ok=True)
            self.count = len([f for f in os.listdir(self.output_dir) if f.lower().endswith(".jpg")])

    def clear_images(self):
        if os.path.exists(self.output_dir):
            deleted_files = 0
            for file in os.listdir(self.output_dir):
                file_path = os.path.join(self.output_dir, file)
                if os.path.isfile(file_path) and file_path.lower().endswith(".jpg"):
                    os.remove(file_path)
                    deleted_files += 1
            self.count = 0
            print(f"Đã xoá {deleted_files} ảnh trong thư mục.")

    def save_image(self):
        if hasattr(self, 'current_frame'):
            filename = os.path.join(self.output_dir, f"img_{self.count:02d}.jpg")
            cv2.imwrite(filename, self.current_frame)
            self.count += 1
            print(f"Đã lưu: {filename}")
        else:
            print("Không có khung hình để lưu.")

    def close_app(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = CameraApp()
    win.show()
    sys.exit(app.exec_())
