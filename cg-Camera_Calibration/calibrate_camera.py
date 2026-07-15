#!/usr/bin/env python3
"""
G2 机器人相机标定脚本
=====================
标定板：7 行 x 11 列棋盘方格 -> 内角点 (10, 6)
即 OpenCV pattern_size = (width=10, height=6)

使用方法：
1. 将标定图片（jpg/png）放入 ./images 文件夹
2. 修改下方 SQUARE_SIZE 为实际方格边长（毫米）
3. 运行: python calibrate_camera.py
4. 结果保存到 calibration_result.json 与 calibration_result.npz

建议：
- 至少采集 15~25 张不同角度、位置的标定板图片
- 标定板应覆盖画面各个区域（中心、四角、边缘）
- 图片大小建议 ≥ 1280x720
"""

import os
import sys
import json
import glob
import cv2
import numpy as np

# ============== 配置 ==============
# 棋盘内角点数 (width, height) = (列数-1, 行数-1)
# 7 行 x 11 列方格 -> 内角点 (10, 6)
PATTERN_SIZE = (10, 6)

# 实际方格边长（毫米），请根据真实标定板修改
SQUARE_SIZE = 25.0

# 标定图片所在目录
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

# 结果保存路径
RESULT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration_result.json")
RESULT_NPZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration_result.npz")

# 是否显示角点检测结果（保存到 ./corners_detected/）
SAVE_CORNER_IMAGES = True
CORNER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corners_detected")
# ==================================


def build_object_points():
    """生成单张标定板的世界坐标点 (Z=0 平面)"""
    pts = np.zeros((PATTERN_SIZE[0] * PATTERN_SIZE[1], 3), dtype=np.float32)
    pts[:, :2] = np.mgrid[0:PATTERN_SIZE[0], 0:PATTERN_SIZE[1]].T.reshape(-1, 2)
    pts *= SQUARE_SIZE
    return pts


def find_corners_in_image(img_gray):
    """在灰度图中检测棋盘角点，返回 (success, corners)"""
    # 优先使用 findChessboardCornersSB（更鲁棒，OpenCV 4.3+）
    try:
        flags = cv2.CALIB_CB_NORMALIZE_MATRIX | cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY
        found, corners = cv2.findChessboardCornersSB(
            img_gray, PATTERN_SIZE, flags=flags
        )
        if found:
            return True, corners
    except AttributeError:
        pass

    # 退回到经典 findChessboardCorners
    found, corners = cv2.findChessboardCorners(
        img_gray, PATTERN_SIZE,
        flags=cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_FILTER_QUADS
    )
    if not found:
        return False, None

    # 亚像素精化
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3)
    corners = cv2.cornerSubPix(img_gray, corners, (11, 11), (-1, -1), criteria)
    return True, corners


def main():
    if not os.path.isdir(IMAGES_DIR):
        print(f"[ERROR] 图片目录不存在: {IMAGES_DIR}")
        print("请先创建 images 文件夹并放入标定图片。")
        sys.exit(1)

    # 支持的图片格式
    patterns = ["*.jpg", "*.jpeg", "*.png", "*.bmp"]
    image_files = []
    for p in patterns:
        image_files.extend(glob.glob(os.path.join(IMAGES_DIR, p)))
        image_files.extend(glob.glob(os.path.join(IMAGES_DIR, p.upper())))
    image_files = sorted(set(image_files))

    if len(image_files) == 0:
        print(f"[ERROR] 在 {IMAGES_DIR} 中未找到图片。")
        sys.exit(1)

    print(f"[INFO] 共找到 {len(image_files)} 张图片")
    print(f"[INFO] 标定板内角点: {PATTERN_SIZE}  方格边长: {SQUARE_SIZE} mm")

    if SAVE_CORNER_IMAGES:
        os.makedirs(CORNER_DIR, exist_ok=True)

    objp = build_object_points()

    obj_points = []  # 3D 世界坐标
    img_points = []  # 2D 图像坐标
    img_size = None
    used_count = 0

    for idx, fp in enumerate(image_files):
        img = cv2.imread(fp)
        if img is None:
            print(f"[WARN] 读取失败，跳过: {fp}")
            continue
        if img_size is None:
            img_size = (img.shape[1], img.shape[0])

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ok, corners = find_corners_in_image(gray)

        if not ok:
            print(f"[WARN] 未检测到角点: {os.path.basename(fp)}")
            continue

        obj_points.append(objp)
        img_points.append(corners)
        used_count += 1
        print(f"[ OK ] {os.path.basename(fp)}  ({used_count} 张有效)")

        if SAVE_CORNER_IMAGES:
            vis = img.copy()
            cv2.drawChessboardCorners(vis, PATTERN_SIZE, corners, True)
            out_name = f"corner_{used_count:03d}_{os.path.basename(fp)}"
            cv2.imwrite(os.path.join(CORNER_DIR, out_name), vis)

    if used_count < 5:
        print(f"[ERROR] 有效图片过少 ({used_count} 张)，至少需要 5 张。")
        sys.exit(1)

    print(f"\n[INFO] 使用 {used_count} 张图片进行标定...")
    print(f"[INFO] 图像尺寸: {img_size}")

    # 执行标定
    flags = 0
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-6)

    ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        obj_points, img_points, img_size, None, None, flags=flags, criteria=criteria
    )

    print("\n========== 标定结果 ==========")
    print(f"RMS 重投影误差: {ret:.6f}")
    print("\n相机内参 camera_matrix (fx, fy, cx, cy):")
    print(camera_matrix)
    print("\n畸变系数 dist_coeffs [k1, k2, p1, p2, k3]:")
    print(dist_coeffs.ravel())

    # 计算每张图片的重投影误差
    per_image_errors = []
    for i in range(len(obj_points)):
        proj, _ = cv2.projectPoints(
            obj_points[i], rvecs[i], tvecs[i], camera_matrix, dist_coeffs
        )
        err = cv2.norm(img_points[i], proj, cv2.NORM_L2) / len(proj)
        per_image_errors.append(float(err))

    print("\n每张图片重投影误差:")
    for i, e in enumerate(per_image_errors):
        print(f"  图片 {i+1:3d}: {e:.4f} px")
    print(f"\n平均: {np.mean(per_image_errors):.4f} px   最大: {np.max(per_image_errors):.4f} px")

    # 保存结果
    result = {
        "image_size": list(img_size),
        "pattern_size": list(PATTERN_SIZE),
        "square_size_mm": SQUARE_SIZE,
        "num_images": used_count,
        "rms_error": float(ret),
        "mean_reproj_error": float(np.mean(per_image_errors)),
        "camera_matrix": camera_matrix.tolist(),
        "dist_coeffs": dist_coeffs.ravel().tolist(),
    }

    with open(RESULT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    np.savez(RESULT_NPZ,
             camera_matrix=camera_matrix,
             dist_coeffs=dist_coeffs,
             rvecs=np.array(rvecs),
             tvecs=np.array(tvecs),
             rms_error=ret,
             per_image_errors=np.array(per_image_errors))

    print(f"\n[OK] 结果已保存:")
    print(f"     JSON: {RESULT_JSON}")
    print(f"     NPZ : {RESULT_NPZ}")
    if SAVE_CORNER_IMAGES:
        print(f"     角点可视化: {CORNER_DIR}")


if __name__ == "__main__":
    main()
