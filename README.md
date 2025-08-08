## Cấu trúc thư mục

DeltaX2_Demo/
├── .vscode/                     # Cấu hình VSCode 
├── __pycache__/                 # File bytecode Python (.pyc) sinh tự động
├── build/                       # File tạm hoặc kết quả biên dịch
├── ByteTrack/                   # Thư viện hoặc module ByteTrack dùng cho tracking đối tượng
├── calibration_images/          
│   └── camera_calib_data.npz    # File dữ liệu nội suy và hiệu chỉnh camera
├── config/                      
│   └── robot_config.json        # Thông số cấu hình robot
├── runs/                      
│   └── best.pt                  # Mô hình YOLO đã train tốt nhất
├── src/                         
│   └── Auto_Offset.py           # Code offset tự động
│   └── Calibration.py           # Code calib camera
│   └── Cap_Detection.py         # Detection bằng OpenCV
│   └── Cap_Tracking.py          # Tracking bằng YOLO, ByteTrack
│   └── Scan_Images.py           # Quét và lưu ảnh từ camera
│   └── Train_YOLO.py            # Train mô hình 
│   └── Test_Model.py            # Test kết quả đã train
├── GUI/                         
│   └── GUI_Auto_Offset.py       # GUI để thực hiện auto offset cho robot
│   └── GUI_Calibration.py       # GUI để thực hiện calib camera
│   └── GUI_Cap_Tracking.py      # GUI để tracking, pick and place
│   └── GUI_Scan_Images.py       # GUI để quét và lưu ảnh từ camera
├── Videos_test/                 # Chứa video dùng để test kết quả train
├── yolo11n.pt                   # Mô hình YOLO11n dùng để train
└── README.md                    # File mô tả 

## Flowchart
'
              ┌──────────────────────┐
              │         Start        │
              └───────────┬──────────┘
                          │
                          ▼
               ┌──────────────────────┐
               │ Chụp ảnh tạo dataset │
               │   (Scan_Images.py)   │
               └───────┬─────┬────────┘
                       │     │
            ┌──────────┘     └────────────┐
            ▼                             ▼
┌──────────────────────┐      ┌──────────────────────┐
│ Calib thông số camera│      │ Huấn luyện mô hình   │
│   (Calibration.py)   │      │  (Train_YOLO.py)     │
└───────────┬──────────┘      └───────────┬──────────┘
            │                             │
            ▼                             ▼
┌──────────────────────┐      ┌──────────────────────┐
│  Tính offset tọa độ  │      │   Kiểm tra mô hình   │
│   (Auto_Offset.py)   │──┐   │   (Test_Model.py)    │
└───────────┬──────────┘  │   └───────────┬──────────┘
            │             │               │
            │             └──────────────►│
            │                             │
            ▼                             ▼
┌──────────────────────┐      ┌──────────────────────┐
│   Object Detection   │      │   Object Tracking    │
│  (Cap_Detection.py)  │      │  (Cap_Tracking.py)   │
└───────────┬──────────┘      └───────────┬──────────┘
            │                             │
            └──────────────┬──────────────┘
                           ▼
               ┌──────────────────────┐
               │          End         │
               └──────────────────────┘


