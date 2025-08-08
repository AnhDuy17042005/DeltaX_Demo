import sys
import os
import cv2
import numpy as np
import glob
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFileDialog, QTextEdit, QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal


class CalibrationThread(QThread):
    result_ready = pyqtSignal(str)

    def __init__(self, image_dir, checkerboard, square_size):
        super().__init__()
        self.image_dir = image_dir
        self.CHECKERBOARD = checkerboard
        self.SQUARE_SIZE = square_size

    def run(self):
        objpoints = []
        imgpoints = []
        objp = np.zeros((1, self.CHECKERBOARD[0] * self.CHECKERBOARD[1], 3), np.float32)
        objp[0, :, :2] = np.mgrid[0:self.CHECKERBOARD[0], 0:self.CHECKERBOARD[1]].T.reshape(-1, 2) * self.SQUARE_SIZE

        images = glob.glob(os.path.join(self.image_dir, "*.jpg"))
        if not images:
            self.result_ready.emit("No .jpg images found in the folder")
            return

        gray = None
        for fname in images:
            img = cv2.imread(fname)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            ret, corners = cv2.findChessboardCorners(
                gray, self.CHECKERBOARD,
                cv2.CALIB_CB_ADAPTIVE_THRESH +
                cv2.CALIB_CB_FAST_CHECK +
                cv2.CALIB_CB_NORMALIZE_IMAGE
            )

            if ret:
                objpoints.append(objp)
                corners2 = cv2.cornerSubPix(
                    gray, corners, (11, 11), (-1, -1),
                    (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                )
                imgpoints.append(corners2)

        if not objpoints or not imgpoints:
            self.result_ready.emit("Not enough checkerboard corners found in the images")
            return

        # Calibration
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
            objpoints, imgpoints, gray.shape[::-1], None, None
        )

        save_path = os.path.join(self.image_dir, "camera_calib_data.npz")
        np.savez(save_path, mtx=mtx, dist=dist)

        result_text = f"Camera matrix:\n{mtx}\n\n"
        result_text += f"Distortion coefficients:\n{dist}\n"
        result_text += f"\nFile saved: {save_path}"
        self.result_ready.emit(result_text)


class CameraCalibrationApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Calibration - PyQt5")
        self.image_dir = ""
        self.CHECKERBOARD = (8, 6)
        self.SQUARE_SIZE = 28

        self.label_info = QLabel("No calibration image folder selected")
        self.btn_select_dir = QPushButton("Select calibration image folder")
        self.btn_calibrate = QPushButton("Calibration")
        self.text_result = QTextEdit()
        self.text_result.setReadOnly(True)

        hbox = QHBoxLayout()
        hbox.addWidget(self.btn_select_dir)
        hbox.addWidget(self.btn_calibrate)

        layout = QVBoxLayout()
        layout.addWidget(self.label_info)
        layout.addLayout(hbox)
        layout.addWidget(QLabel("Calibration Result:"))
        layout.addWidget(self.text_result)
        self.setLayout(layout)

        self.btn_select_dir.clicked.connect(self.select_directory)
        self.btn_calibrate.clicked.connect(self.start_calibration)

    def select_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Select the folder containing calibration images")
        if folder:
            self.image_dir = folder
            self.label_info.setText(f"Folder: {self.image_dir}")

    def start_calibration(self):
        if not self.image_dir:
            QMessageBox.warning(self, "Error", "You have not selected a calibration image folder")
            return
        self.text_result.setPlainText("Running calibration, please wait...")
        self.calib_thread = CalibrationThread(self.image_dir, self.CHECKERBOARD, self.SQUARE_SIZE)
        self.calib_thread.result_ready.connect(self.show_result)
        self.calib_thread.start()

    def show_result(self, text):
        self.text_result.setPlainText(text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = CameraCalibrationApp()
    win.resize(600, 400)
    win.show()
    sys.exit(app.exec_())
