#!/usr/bin/env python3
"""
仅拍摄 1 张 头部彩色相机 并保存图片
"""

import time
import os
import agibot_gdk

# 初始化相机
camera = agibot_gdk.Camera()
time.sleep(2)

# 只使用头部彩色相机
cam_type = agibot_gdk.CameraType.kHeadColor

try:
    # 获取一帧图像
    img = camera.get_latest_image(cam_type, 1000.0)

    if img is not None:
        print(f"拍摄成功：{img.width}x{img.height}")

        # 保存图片
        os.makedirs("images", exist_ok=True)
        
        # 获取当前时间（格式：YYYYMMDD_HHMMSS，包含秒数）
        time_str = time.strftime("%Y%m%d_%H%M%S")
        filename = f"images/head_color_{time_str}.jpg"
        
        # 如果你只想要纯数字的累计秒数 (Epoch time)，可以使用下面这行代替上面两行：
        # filename = f"images/head_color_{int(time.time())}.jpg"

        with open(filename, "wb") as f:
            f.write(img.data)

        print(f"图片已保存：{filename}")
    else:
        print("未获取到图像")

finally:
    camera.close_camera()