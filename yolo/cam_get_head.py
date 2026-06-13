#!/usr/bin/env python3
"""
拍摄 头部彩色相机 + 头部深度相机，保存彩色图和深度图（原始 uint16 + 伪彩色）
"""

import time
import os
import numpy as np
import agibot_gdk

# 初始化相机
camera = agibot_gdk.Camera()
time.sleep(2)

os.makedirs("images", exist_ok=True)

try:
    # ========== 1. 拍摄彩色图 ==========
    color_type = agibot_gdk.CameraType.kHeadColor
    color_img = camera.get_latest_image(color_type, 1000.0)

    if color_img is not None:
        print(f"彩色相机：{color_img.width}x{color_img.height}")
        filename = "head.jpg"
        with open(filename, "wb") as f:
            f.write(color_img.data)
        print(f"彩色图已保存：{filename}")
    else:
        print("未获取到彩色图像")

    # ========== 2. 拍摄深度图 ==========
    depth_type = agibot_gdk.CameraType.kHeadDepth
    depth_img = camera.get_latest_image(depth_type, 1000.0)

    if depth_img is not None:
        print(f"深度相机：{depth_img.width}x{depth_img.height}, encoding={depth_img.encoding}")

        # --- 2a. 保存原始深度数据（uint16 二进制） ---
        depth_raw_filename = "head_depth.raw"
        with open(depth_raw_filename, "wb") as f:
            f.write(depth_img.data)
        print(f"原始深度数据已保存：{depth_raw_filename}")

        # --- 2b. 解码为 uint16 数组并保存为伪彩色图 ---
        try:
            import cv2

            # 解析深度数据（假设为 uint16 / Z16）
            depth_array = np.frombuffer(depth_img.data, dtype=np.uint16)
            depth_array = depth_array.reshape((depth_img.height, depth_img.width))

            # 统计有效深度范围
            valid_mask = depth_array > 0
            if np.any(valid_mask):
                min_d = depth_array[valid_mask].min()
                max_d = depth_array[valid_mask].max()
                print(f"深度范围：{min_d} ~ {max_d} mm")
            else:
                min_d, max_d = 0, 1
                print("深度图全部为 0（无效）")

            # 归一化 + 伪彩色
            if max_d > min_d:
                normalized = ((depth_array - min_d) / (max_d - min_d) * 255).astype(np.uint8)
            else:
                normalized = np.zeros_like(depth_array, dtype=np.uint8)
            depth_colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)

            # 在图上标注深度范围
            depth_info = f"Depth: {min_d}-{max_d}mm"
            cv2.putText(depth_colored, depth_info, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            depth_jpg_filename = "head_depth.jpg"
            cv2.imwrite(depth_jpg_filename, depth_colored)
            print(f"深度伪彩色图已保存：{depth_jpg_filename}")

        except ImportError:
            print("⚠️ OpenCV 未安装，跳过深度图伪彩色保存")
        except Exception as e:
            print(f"⚠️ 深度图处理失败：{e}")
    else:
        print("未获取到深度图像")

finally:
    camera.close_camera()