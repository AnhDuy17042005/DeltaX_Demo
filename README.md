# Vision-Based Bottle Cap Detection & Robotic Pick-and-Place System

The `bottle cap pick-and-place` system uses a `camera`, `Delta robot`, `coordinate calibration`, and two computer vision pipelines to detect caps moving on a conveyor belt, convert image coordinates to millimeters, compensate for motion delay, and control the robot to pick caps by color.

## Demo

<div align="center">
  <video src="https://github.com/user-attachments/assets/fe32c54f-1c9a-4f04-bf25-05be78b2fe0b" controls width="420"></video>
</div>

## Key Features

- Calibrate the camera using a checkerboard and save `camera_calib_data.npz`.
- Compute `OFFSET_X`, `OFFSET_Y` to map from the camera coordinate system to the robot coordinate system.
- Support two image processing pipelines:
  - `src/Classic_CV_Tracking.py`: classical image processing with OpenCV.
  - `src/DL_Tracking.py`: Deep Learning with YOLO + ByteTrack.
- Control the Delta robot with G-code via a serial port.
- Provide GUIs for image scanning, calibration, offset calculation, and system operation.

## Environment Setup

### Requirements

- Python and `pip`
- Camera used to observe the working area
- Delta robot connected via serial if running real hardware
- Weights at `runs/detect/train/weights/best.pt` if using the Deep Learning pipeline
- Labeled dataset and `data.yaml` if retraining the model

### Create a Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### Install Libraries

```bash
pip install -r requirements.txt
```

If running YOLO with a GPU, it is recommended to install the `PyTorch` version suitable for your machine before installing the remaining dependencies.

## How to Run

The actual entry point is:

```bash
python GUI/GUI_Tracking.py
```

Common commands:

| Purpose | Command |
| --- | --- |
| Capture and save images from the camera | `python GUI/GUI_Scan_Images.py` |
| Camera calibration | `python GUI/GUI_Calibration.py` |
| Calculate camera -> robot offset | `python GUI/GUI_Auto_Offset.py` |
| Run the integrated control interface | `python GUI/GUI_Tracking.py` |
| Capture images with a script | `python src/Scan_Images.py` |
| Calibration with a script | `python src/Calibration.py` |
| Calculate offset with a script | `python src/Auto_Offset.py` |
| Train YOLO | `python src/Train_YOLO.py` |
| Test the YOLO model | `python src/Test_Model.py` |
| Run the classical pipeline | `python src/Classic_CV_Tracking.py` |
| Run the Deep Learning pipeline | `python src/DL_Tracking.py` |

## Recommended Operation Workflow

1. Collect checkerboard images using `GUI/GUI_Scan_Images.py` or `src/Scan_Images.py`.
2. Run calibration to create `camera_calib_data.npz`.
3. Run auto offset to obtain `OFFSET_X`, `OFFSET_Y`.
4. If using Deep Learning, prepare the dataset and `data.yaml`, then train/test the model.
5. Operate the system using `GUI/GUI_Tracking.py` or the scripts in `src/`.

## System Architecture

The project is organized around two main flows:

- `Image processing flow`
  - Read frames from the camera
  - Detect or track bottle caps
  - Calculate the object center
  - Convert from pixels to millimeters using calibration data
  - Put the target into a `PriorityQueue`

- `Delta robot control flow`
  - Get the target from the queue
  - Compensate for delay based on conveyor speed and processing latency
  - Add the offset to convert from the camera coordinate system to the robot coordinate system
  - Send G-code so the robot performs pick-and-place

## Two Image Processing Pipelines

### `src/Classic_CV_Tracking.py`

Classical OpenCV pipeline, suitable when lighting is stable:

- Segment colors in the `HSV` space
- Filter noise with morphology
- Find contours and check shapes
- Calculate cap centers and convert coordinates to millimeters
- Put valid objects into the queue

### `src/DL_Tracking.py`

Deep Learning pipeline for more complex real-world environments:

- Load YOLO from `runs/detect/train/weights/best.pt`
- Track with ByteTrack through `model.track(...)`
- Get `track_id`, class, and bounding box center
- Convert coordinates to millimeters
- Queue targets so the robot picks them by color

## Directory Structure

```text
Demo_TrackingCap/
|-- ByteTrack/                     # ByteTrack source code included in the repo
|-- Config/
|   `-- robot_config.json          # Robot, camera, offset, and timing configuration
|-- GUI/
|   |-- GUI_Auto_Offset.py         # GUI for calculating camera -> robot offset
|   |-- GUI_Calibration.py         # GUI for camera calibration
|   |-- GUI_Scan_Images.py         # GUI for capturing and saving images
|   `-- GUI_Tracking.py            # GUI for controlling the tracking + robot system
|-- calibration_images/
|   `-- camera_calib_data.npz      # Camera calibration data
|-- runs/
|   `-- detect/train/weights/
|       |-- best.pt                # Best weights after training
|       `-- last.pt                # Final weights
|-- src/
|   |-- Auto_Offset.py             # Calculate offset
|   |-- Calibration.py             # Camera calibration
|   |-- Classic_CV_Tracking.py     # Classical image processing pipeline
|   |-- DL_Tracking.py             # YOLO + ByteTrack pipeline
|   |-- Scan_Images.py             # Capture and save images
|   |-- Test_Model.py              # Test the model on video
|   `-- Train_YOLO.py              # Train the YOLO model
|-- Videos_test/                   # Test videos
|-- build/                         # Build/debug files
|-- requirements.txt               # List of required libraries
|-- yolo11n.pt                     # Initial weights for training
`-- README.md
```

## Main Components

- `GUI/GUI_Tracking.py`: integrated control application, best suited for running the system.
- `src/Calibration.py` and `GUI/GUI_Calibration.py`: create camera calibration data.
- `src/Auto_Offset.py` and `GUI/GUI_Auto_Offset.py`: calculate the offset between the camera and robot.
- `src/Train_YOLO.py`: train the model from `yolo11n.pt`.
- `src/Test_Model.py`: quickly evaluate the model on a sample video.

## Notes

- Some scripts use absolute paths from the development machine. When running on another machine, update the paths to the calibration file or test video.
- `src/Train_YOLO.py` requires `data.yaml`, but this file is currently not available in the repo.
- The serial opening section in `src/Classic_CV_Tracking.py` and `src/DL_Tracking.py` is currently commented out; `GUI/GUI_Tracking.py` is the clearest place where the real robot is connected.
- To avoid relative config errors, run commands from the repo root directory.
