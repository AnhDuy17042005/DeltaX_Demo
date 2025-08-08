import sys
import cv2
import numpy as np
import serial
import time
import threading
import queue
import math
import json
import os
from ultralytics import YOLO
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QGroupBox, QGridLayout, 
                             QComboBox, QTabWidget, QTextEdit, QMessageBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

class VideoWidget(QWidget):
    update_frame = pyqtSignal(np.ndarray)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setMinimumSize(640, 480)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.update_frame.connect(self.update_image)
    
    def update_image(self, frame):
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.label.width(), self.label.height(), Qt.KeepAspectRatio)
        self.label.setPixmap(QPixmap.fromImage(p))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Control System")
        self.setGeometry(100, 100, 1200, 800)
        
        # Variables
        self.cap = None
        self.ser = None
        self.model = None
        self.task_queue = queue.PriorityQueue()
        self.is_picking = False
        self.is_running = False
        self.camera_thread = None
        self.robot_thread = None
        self.config_file = "robot_config.json"
        
        # Load default values from config file
        self.defaults = self.load_config()
        
        self.init_ui()
        self.load_defaults()
        
    def load_config(self):
        """Load configuration from file or return defaults"""
        defaults = {
            'com_port': 'COM',
            'baud_rate': '115200',
            'camera_id': '0',
            'z_pick': '-370',
            'z_move': '-352',
            'z': '465',
            'distance_threshold': '25.0',
            'v_belt': '40.0',
            'processing_delay': '0.35',
            'robot_delay': '0.35',
            'offset_x': '-4.2',
            'offset_y': '276',
            'white_x': '110',
            'white_y': '0',
            'blue_x': '150',
            'blue_y': '0',
            'red_x': '110',
            'red_y': '-40',
        }
        
        # Try to load saved configuration
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    # Update defaults with saved values
                    defaults.update(saved_config)
                    print("Configuration loaded from file")
            except Exception as e:
                print(f"Error loading config: {e}")
        
        return defaults
    
    def save_config(self):
        """Save current configuration to file"""
        config = {
            'com_port': self.com_port_edit.text(),
            'baud_rate': self.baud_rate_edit.text(),
            'camera_id': self.camera_id_edit.text(),
            'z_pick': self.z_pick_edit.text(),
            'z_move': self.z_move_edit.text(),
            'z': self.z_edit.text(),
            'distance_threshold': self.distance_threshold_edit.text(),
            'v_belt': self.v_belt_edit.text(),
            'processing_delay': self.processing_delay_edit.text(),
            'robot_delay': self.robot_delay_edit.text(),
            'offset_x': self.offset_x_edit.text(),
            'offset_y': self.offset_y_edit.text(),
            'white_x': self.white_x_edit.text(),
            'white_y': self.white_y_edit.text(),
            'blue_x': self.blue_x_edit.text(),
            'blue_y': self.blue_y_edit.text(),
            'red_x': self.red_x_edit.text(),
            'red_y': self.red_y_edit.text(),
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            self.log_message("Configuration saved successfully")
        except Exception as e:
            self.log_message(f"Error saving config: {e}")
            QMessageBox.warning(self, "Save Error", f"Failed to save configuration: {str(e)}")
        
    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Create tabs
        tabs = QTabWidget()
        
        # Control Tab
        control_tab = QWidget()
        control_layout = QGridLayout()
        
        # Camera Settings
        camera_group = QGroupBox("Camera Settings")
        camera_layout = QGridLayout()
        self.camera_id_edit = QLineEdit()
        camera_layout.addWidget(QLabel("Camera ID:"), 0, 0)
        camera_layout.addWidget(self.camera_id_edit, 0, 1)
        camera_group.setLayout(camera_layout)
        
        # Robot Settings
        robot_group = QGroupBox("Robot Settings")
        robot_layout = QGridLayout()
        self.com_port_edit = QLineEdit()
        self.baud_rate_edit = QLineEdit()
        robot_layout.addWidget(QLabel("COM Port:"), 0, 0)
        robot_layout.addWidget(self.com_port_edit, 0, 1)
        robot_layout.addWidget(QLabel("Baud Rate:"), 1, 0)
        robot_layout.addWidget(self.baud_rate_edit, 1, 1)
        robot_group.setLayout(robot_layout)
        
        # Z Settings
        z_group = QGroupBox("Z Settings")
        z_layout = QGridLayout()
        self.z_pick_edit = QLineEdit()
        self.z_move_edit = QLineEdit()
        self.z_edit = QLineEdit()
        z_layout.addWidget(QLabel("Z Pick:"), 0, 0)
        z_layout.addWidget(self.z_pick_edit, 0, 1)
        z_layout.addWidget(QLabel("Z Move:"), 1, 0)
        z_layout.addWidget(self.z_move_edit, 1, 1)
        z_layout.addWidget(QLabel("Z:"), 2, 0)
        z_layout.addWidget(self.z_edit, 2, 1)
        z_group.setLayout(z_layout)
        
        # Drop Zones
        drop_group = QGroupBox("Drop Zones")
        drop_layout = QGridLayout()
        self.white_x_edit = QLineEdit()
        self.white_y_edit = QLineEdit()
        self.blue_x_edit = QLineEdit()
        self.blue_y_edit = QLineEdit()
        self.red_x_edit = QLineEdit()
        self.red_y_edit = QLineEdit()
        
        drop_layout.addWidget(QLabel("White X:"), 0, 0)
        drop_layout.addWidget(self.white_x_edit, 0, 1)
        drop_layout.addWidget(QLabel("White Y:"), 0, 2)
        drop_layout.addWidget(self.white_y_edit, 0, 3)
        drop_layout.addWidget(QLabel("Blue X:"), 1, 0)
        drop_layout.addWidget(self.blue_x_edit, 1, 1)
        drop_layout.addWidget(QLabel("Blue Y:"), 1, 2)
        drop_layout.addWidget(self.blue_y_edit, 1, 3)
        drop_layout.addWidget(QLabel("Red X:"), 2, 0)
        drop_layout.addWidget(self.red_x_edit, 2, 1)
        drop_layout.addWidget(QLabel("Red Y:"), 2, 2)
        drop_layout.addWidget(self.red_y_edit, 2, 3)
        drop_group.setLayout(drop_layout)
        
        # Offset Settings
        offset_group = QGroupBox("Offset Settings")
        offset_layout = QGridLayout()
        self.offset_x_edit = QLineEdit()
        self.offset_y_edit = QLineEdit()
        offset_layout.addWidget(QLabel("Offset X:"), 0, 0)
        offset_layout.addWidget(self.offset_x_edit, 0, 1)
        offset_layout.addWidget(QLabel("Offset Y:"), 1, 0)
        offset_layout.addWidget(self.offset_y_edit, 1, 1)
        offset_group.setLayout(offset_layout)
        
        # Timing Settings
        timing_group = QGroupBox("Timing Settings")
        timing_layout = QGridLayout()
        self.distance_threshold_edit = QLineEdit()
        self.v_belt_edit = QLineEdit()
        self.processing_delay_edit = QLineEdit()
        self.robot_delay_edit = QLineEdit()
        timing_layout.addWidget(QLabel("Distance Threshold:"), 0, 0)
        timing_layout.addWidget(self.distance_threshold_edit, 0, 1)
        timing_layout.addWidget(QLabel("Belt Speed:"), 1, 0)
        timing_layout.addWidget(self.v_belt_edit, 1, 1)
        timing_layout.addWidget(QLabel("Processing Delay:"), 2, 0)
        timing_layout.addWidget(self.processing_delay_edit, 2, 1)
        timing_layout.addWidget(QLabel("Robot Reaction Delay:"), 3, 0)
        timing_layout.addWidget(self.robot_delay_edit, 3, 1)
        timing_group.setLayout(timing_layout)
        
        # Buttons
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_system)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_system)
        self.stop_btn.setEnabled(False)
        self.home_btn = QPushButton("Go Home")
        self.home_btn.clicked.connect(self.go_home)
        self.home_btn.setEnabled(False)
        self.save_config_btn = QPushButton("Save Config")
        self.save_config_btn.clicked.connect(self.save_config)
        
        # Add to control layout
        control_layout.addWidget(camera_group, 0, 0, 1, 2)
        control_layout.addWidget(robot_group, 1, 0, 1, 2)
        control_layout.addWidget(z_group, 2, 0)
        control_layout.addWidget(offset_group, 2, 1)
        control_layout.addWidget(timing_group, 3, 0)
        control_layout.addWidget(drop_group, 3, 1)
        control_layout.addWidget(self.start_btn, 4, 0)
        control_layout.addWidget(self.stop_btn, 4, 1)
        control_layout.addWidget(self.home_btn, 5, 0)
        control_layout.addWidget(self.save_config_btn, 5, 1)
        
        control_tab.setLayout(control_layout)
        
        # Camera Tab
        camera_tab = QWidget()

        # Layout chính: nằm ngang
        camera_tab_layout = QHBoxLayout()
        self.video_widget = VideoWidget()
        camera_tab_layout.addWidget(self.video_widget, 2)

        log_layout = QVBoxLayout()
        log_label = QLabel("System Log:")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_text)

        log_widget = QWidget()
        log_widget.setLayout(log_layout)
        camera_tab_layout.addWidget(log_widget, 1)
        camera_tab.setLayout(camera_tab_layout)

        # Add tabs
        tabs.addTab(control_tab, "Control")
        tabs.addTab(camera_tab, "Camera")
        
        main_layout.addWidget(tabs)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Status Bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("System Ready")
        
    def load_defaults(self):
        self.camera_id_edit.setText(self.defaults['camera_id'])
        self.com_port_edit.setText(self.defaults['com_port'])
        self.baud_rate_edit.setText(self.defaults['baud_rate'])
        self.z_pick_edit.setText(self.defaults['z_pick'])
        self.z_move_edit.setText(self.defaults['z_move'])
        self.z_edit.setText(self.defaults['z'])
        self.offset_x_edit.setText(self.defaults['offset_x'])
        self.offset_y_edit.setText(self.defaults['offset_y'])
        self.white_x_edit.setText(self.defaults['white_x'])
        self.white_y_edit.setText(self.defaults['white_y'])
        self.blue_x_edit.setText(self.defaults['blue_x'])
        self.blue_y_edit.setText(self.defaults['blue_y'])
        self.red_x_edit.setText(self.defaults['red_x'])
        self.red_y_edit.setText(self.defaults['red_y'])
        self.distance_threshold_edit.setText(self.defaults['distance_threshold'])
        self.v_belt_edit.setText(self.defaults['v_belt'])
        self.processing_delay_edit.setText(self.defaults['processing_delay'])
        self.robot_delay_edit.setText(self.defaults['robot_delay'])
    
    def log_message(self, message):
        self.log_text.append(f"[{time.strftime('%H:%M:%S')}] {message}")
        self.status_bar.showMessage(message)
    
    def start_system(self):
        if self.is_running:
            return
            
        try:
            # Get parameters from UI
            camera_id = int(self.camera_id_edit.text())
            com_port = self.com_port_edit.text()
            baud_rate = int(self.baud_rate_edit.text())
            
            # Initialize camera
            self.cap = cv2.VideoCapture(camera_id)
            if not self.cap.isOpened():
                raise Exception("Cannot open camera")
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Initialize serial connection
            self.ser = serial.Serial(com_port, baud_rate, timeout=1)
            time.sleep(2)
            
            # Load YOLO model
            self.model = YOLO('runs/detect/train/weights/best.pt')
            
            # Load calibration data
            data = np.load(r"D:\StudyDocuments_at_BKU\Python\DeltaX2_Demo\calibration_images\camera_calib_data.npz")

            self.mtx = data['mtx']
            self.dist = data['dist']
            self.fx = self.mtx[0, 0]
            self.fy = self.mtx[1, 1]
            self.cx = self.mtx[0, 2]
            self.cy = self.mtx[1, 2]
            
            # Set parameters
            self.Z_PICK = float(self.z_pick_edit.text())
            self.Z_MOVE = float(self.z_move_edit.text())
            self.Z = float(self.z_edit.text())
            self.OFFSET_X = float(self.offset_x_edit.text())
            self.OFFSET_Y = float(self.offset_y_edit.text())
            
            # Timing parameters
            self.DISTANCE_THRESHOLD = float(self.distance_threshold_edit.text())
            self.V_BELT = float(self.v_belt_edit.text())
            self.PROCESSING_DELAY = float(self.processing_delay_edit.text())
            self.ROBOT_REACTION_DELAY = float(self.robot_delay_edit.text())
            self.TOTAL_DELAY = self.PROCESSING_DELAY + self.ROBOT_REACTION_DELAY
            self.OFFSET_DELAY = self.V_BELT / 40
            
            # Drop zones
            self.drop_zones = {
                'white': (float(self.white_x_edit.text()), float(self.white_y_edit.text())),
                'blue': (float(self.blue_x_edit.text()), float(self.blue_y_edit.text())),
                'red': (float(self.red_x_edit.text()), float(self.red_y_edit.text())),
            }
            
            # Calculate mm per pixel
            self.mm_per_pixel_x = self.Z / self.fx
            self.mm_per_pixel_y = self.Z / self.fy
            
            # Initialize robot thread
            self.is_running = True
            self.is_picking = False
            self.robot_thread = threading.Thread(target=self.deltaX2_thread, daemon=True)
            self.robot_thread.start()
            
            # Initialize camera timer
            self.timer = QTimer()
            self.timer.timeout.connect(self.process_frame)
            self.timer.start(30) 
            
            # Send initialization commands
            self.send_gcode("G28", wait=1)
            self.send_gcode("M360 E0", wait=1)
            
            # Update UI
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.home_btn.setEnabled(True)
            self.log_message("System started successfully")
            
        except Exception as e:
            self.log_message(f"Error starting system: {str(e)}")
            QMessageBox.critical(self, "Start Error", f"Failed to start system: {str(e)}")
            self.stop_system()
    
    def stop_system(self):
        if not self.is_running:
            return
            
        self.is_running = False
        
        # Stop timer
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        
        # Release camera
        if self.cap and self.cap.isOpened():
            self.cap.release()
        
        # Close serial connection
        if self.ser and self.ser.is_open:
            self.ser.close()
        
        # Update UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.home_btn.setEnabled(False)
        self.log_message("System stopped")
    
    def go_home(self):
        if self.ser and self.ser.is_open:
            self.send_gcode("G28", wait=1)
            self.log_message("Robot returned to home position")
    
    def send_gcode(self, cmd, wait=0.5):
        if self.ser and self.ser.is_open:
            self.ser.write((cmd + '\n').encode('utf-8'))
            self.log_message(f"Sent G-code: {cmd}")
            time.sleep(wait)
    
    def process_frame(self):
        if not self.is_running or self.is_picking or not self.cap.isOpened():
            return
            
        ret, frame = self.cap.read()
        if not ret:
            self.log_message("Failed to capture frame")
            return
            
        img_with_boxes = frame.copy()
        frame_detections = []
        
        # Process with YOLO
        if self.model:
            results = self.model.track(
                frame,
                imgsz=640,
                conf=0.3,
                persist=True,
                tracker="bytetrack.yaml",
                verbose=False
            )
            
            if len(results):
                img_with_boxes = results[0].plot()
                
                # Vùng ROI
                h, w = img_with_boxes.shape[:2]
                x1_roi = int(w * 0.4)
                x2_roi = int(w * 0.6)
                x1_roi_mm = -(x1_roi - self.cx) * self.mm_per_pixel_x
                x2_roi_mm = -(x2_roi - self.cx) * self.mm_per_pixel_x

                cv2.rectangle(img_with_boxes, (x1_roi + 10, 0), (x2_roi + 10, h), (255, 0, 0), 2)
                for box in results[0].boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    class_id = int(box.cls[0].cpu().numpy())
                    color_name = self.model.names[class_id]
                    confident = float(box.conf[0].cpu().numpy())
                    
                    # Skip small objects
                    S = (x2 - x1) * (y2 - y1)
                    if S < 700:
                        continue
                    
                    if box.id is None:
                        continue
                    
                    try:
                        track_id = int(box.id.item())
                    except:
                        continue
                    
                    center = (int((x1 + x2)/2), int((y1 + y2)/2))
                    
                    # Convert to mm
                    center_x_mm = -(center[0] - self.cx) * self.mm_per_pixel_x
                    center_y_mm = (center[1] - self.cy) * self.mm_per_pixel_y
                    
                    if center_x_mm < x2_roi_mm or center_x_mm  > x1_roi_mm:
                        print("Toạ độ ngoài phạm vi vùng ROI , bỏ qua")
                        continue

                    frame_detections.append((track_id, center_x_mm, center_y_mm, color_name))
        
        # Add to task queue
        detection_time = time.time()
        for tid, x_mm, y_mm, cname in sorted(frame_detections, key=lambda t: t[2]):
            self.task_queue.put(((y_mm, time.time()), (detection_time, x_mm, y_mm, cname, tid)))
            self.log_message(f"Queued: ID={tid} | {cname} | ({x_mm:.1f}, {y_mm:.1f})")
        
        # Convert to RGB for display
        img_rgb = cv2.cvtColor(img_with_boxes, cv2.COLOR_BGR2RGB)
        self.video_widget.update_frame.emit(img_rgb)
    
    def deltaX2_thread(self):
        last_detection_time = time.time()
        NO_CAP_TIMEOUT = 15.0
        has_returned_home = False
        
        while self.is_running:
            try:
                # Get task from queue
                priority, (detection_time, x_mm, y_mm, color_name, tid) = self.task_queue.get(timeout=1)
                current_time = time.time()
                
                # Calculate compensation
                total_delay = current_time - detection_time + self.TOTAL_DELAY
                y_compensated = y_mm - self.V_BELT * total_delay - self.OFFSET_DELAY
                
                last_detection_time = current_time
                
                # Apply offsets
                robot_x = x_mm + self.OFFSET_X
                robot_y = y_compensated + self.OFFSET_Y
                
                # Check boundaries
                if robot_y > 160 or robot_y < -160:
                    self.log_message(f"Out of range: ({robot_x:.1f}, {robot_y:.1f})")
                    continue
                
                # Get drop zone
                drop_x, drop_y = self.drop_zones[color_name]
                
                self.log_message(f"Picking {color_name} cap at ({robot_x:.1f}, {robot_y:.1f})")
                
                self.is_picking = True
                
                # Execute pick and place
                self.send_gcode(f"G1 X{robot_x:.2f} Y{robot_y:.2f} Z{self.Z_MOVE} F600", wait=0.5)
                self.send_gcode(f"G1 Z{self.Z_PICK} F1400", wait=0)
                self.send_gcode("M03", wait=0)
                self.send_gcode(f"G1 Z{self.Z_MOVE} F1400", wait=0.5)
                self.send_gcode(f"G1 X{drop_x} Y{drop_y} Z{self.Z_MOVE} F600", wait=0.5)
                self.send_gcode("M05", wait=0.75)
                
                self.is_picking = False
                last_detection_time = current_time
                has_returned_home = False
                
            except queue.Empty:
                # Return home if no detections for a while
                if time.time() - last_detection_time > NO_CAP_TIMEOUT and not has_returned_home:
                    self.send_gcode("G28", wait=1)
                    self.log_message("No caps detected - returning home")
                    has_returned_home = True
                continue
    
    def closeEvent(self, event):
        """Save configuration when closing the application"""
        self.save_config()
        self.stop_system()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())