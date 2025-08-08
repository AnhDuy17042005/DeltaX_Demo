import cv2
import numpy as np
import os
import glob

# Định nghĩa kích thước của checkerboard
CHECKERBOARD = (8, 6)
SQUARE_SIZE = 28 
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# Tạo vector để lưu trữ các điểm 3D
objpoints = []
# Tạo vector để lưu trữ các điểm 2D 
imgpoints = []

objp = np.zeros((1, CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[0, :, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)* SQUARE_SIZE
pre_img_shape = None

images = glob.glob('./calibration_images/*.jpg')
if not images:
    print("Không tìm thấy ảnh trong thư mục calibration_images!")
    exit()

for fname in images:
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Tìm các góc của checkerboard
    ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, cv2.CALIB_CB_ADAPTIVE_THRESH
                                             + cv2.CALIB_CB_FAST_CHECK + cv2.CALIB_CB_NORMALIZE_IMAGE)    
    if ret == True:
        objpoints.append(objp)

        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)
        
        # Hiển thị kết quả
        cv2.drawChessboardCorners(img, CHECKERBOARD, corners2, ret)
    cv2.imshow('img', img)
    cv2.waitKey(0)
cv2.destroyAllWindows()

h, w = img.shape[:2]

# Lấy ma trận camera và hệ số biến dạng
ret, mtx, dist, rvecs, tvecs =  cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
np.savez('camera_calib_data.npz', mtx = mtx, dist = dist)


print("Camera matrix:\n", mtx)
print("Distortion coefficients:\n", dist)
# print("rvecs:\n", rvecs)
# print("tvecs:\n", tvecs)