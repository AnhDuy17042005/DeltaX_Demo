import sys
import cv2
import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore

class OffsetCalibration(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Auto OFFSET Calibration")
        self.setGeometry(200, 100, 900, 700)

        # Load camera calibration data
        data = np.load(r"D:\StudyDocuments_at_BKU\Python\DeltaX2_Demo\calibration_images\camera_calib_data.npz")
        self.mtx = data['mtx']
        self.dist = data['dist']

        # Camera intrinsic parameters
        self.fx = self.mtx[0, 0]
        self.fy = self.mtx[1, 1]
        self.cx = self.mtx[0, 2]
        self.cy = self.mtx[1, 2]
        self.Z = 465  # mm - khoảng cách từ camera đến băng tải

        # Pixel → mm conversion
        self.mm_per_pixel_x = self.Z / self.fx
        self.mm_per_pixel_y = self.Z / self.fy

        # Camera
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise Exception("Không thể mở camera")

        # UI Layout
        layout = QtWidgets.QVBoxLayout(self)

        # Video display
        self.video_label = QtWidgets.QLabel()
        layout.addWidget(self.video_label)

        # Form nhập tọa độ robot
        form_layout = QtWidgets.QFormLayout()
        self.x_robot_input = QtWidgets.QLineEdit()
        self.y_robot_input = QtWidgets.QLineEdit()
        form_layout.addRow("X Robot (mm):", self.x_robot_input)
        form_layout.addRow("Y Robot (mm):", self.y_robot_input)
        layout.addLayout(form_layout)

        # Button tính OFFSET
        self.calc_button = QtWidgets.QPushButton("Tính OFFSET")
        self.calc_button.clicked.connect(self.calculate_offset)
        layout.addWidget(self.calc_button)

        # Hiển thị kết quả
        self.result_label = QtWidgets.QLabel("OFFSET_X = ? , OFFSET_Y = ?")
        layout.addWidget(self.result_label)

        # Điểm click
        self.clicked_point = None

        # Timer cập nhật video
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        # Sự kiện click chuột trên video
        self.video_label.mousePressEvent = self.get_mouse_position

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        # Vẽ điểm gốc (0,0) trên ảnh
        cv2.circle(frame, (int(self.cx), int(self.cy)), 4, (0, 255, 255), -1)
        cv2.putText(frame, "Goc (0,0)", (int(self.cx)+5, int(self.cy)-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # Vẽ điểm đã click
        if self.clicked_point:
            cv2.circle(frame, self.clicked_point, 5, (0, 0, 255), -1)

        # Chuyển OpenCV image → Qt pixmap
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        self.video_label.setPixmap(QtGui.QPixmap.fromImage(qt_image))

    def get_mouse_position(self, event):
        if self.video_label.pixmap() is None:
            return
        x = int(event.pos().x())
        y = int(event.pos().y())

        # Lưu tọa độ pixel
        self.clicked_point = (x, y)

        # Tính tọa độ camera mm
        self.x_mm = -(x - self.cx) * self.mm_per_pixel_x
        self.y_mm = (y - self.cy) * self.mm_per_pixel_y

        self.result_label.setText(f"Tọa độ camera: ({self.x_mm:.2f}, {self.y_mm:.2f}) mm")

    def calculate_offset(self):
        if self.clicked_point is None:
            self.result_label.setText("Hãy click chọn điểm trên video trước!")
            return
        try:
            X_robot = float(self.x_robot_input.text())
            Y_robot = float(self.y_robot_input.text())

            OFFSET_X = X_robot - self.x_mm
            OFFSET_Y = Y_robot - self.y_mm

            self.result_label.setText(f"OFFSET_X = {OFFSET_X:.2f} mm, OFFSET_Y = {OFFSET_Y:.2f} mm")
        except ValueError:
            self.result_label.setText("Lỗi: Nhập tọa độ robot không hợp lệ!")

    def closeEvent(self, event):
        self.cap.release()
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = OffsetCalibration()
    window.show()
    sys.exit(app.exec_())
