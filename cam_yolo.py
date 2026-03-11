#!/usr/bin/env python3
"""
仅拍摄 1 张 头部彩色相机 并保存图片 + YOLO目标检测
"""

import time
import os
import agibot_gdk
import numpy as np
import cv2  # 必须导入OpenCV用于图像解码
from ultralytics import YOLO

# 加载预训练模型
model = YOLO('yolov8n.pt')
# 初始化相机
camera = agibot_gdk.Camera()
time.sleep(2)

# 只使用头部彩色相机
cam_type = agibot_gdk.CameraType.kHeadColor

def decode_camera_image(image) -> np.ndarray:
    """将agibot_gdk的CameraImage对象解码为OpenCV格式的图像"""
    if not hasattr(image, 'data') or not image.data.any():
        raise ValueError("图像数据为空")
    
    # 处理最常见的JPEG编码
    if image.encoding == agibot_gdk.Encoding.JPEG:
        nparr = np.frombuffer(image.data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    # 兼容未压缩格式（备用）
    elif image.encoding == agibot_gdk.Encoding.UNCOMPRESSED:
        if image.color_format == agibot_gdk.ColorFormat.RGB:
            img = np.frombuffer(image.data, dtype=np.uint8).reshape((image.height, image.width, 3))
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)  # 转OpenCV默认的BGR格式
        elif image.color_format == agibot_gdk.ColorFormat.BGR:
            img = np.frombuffer(image.data, dtype=np.uint8).reshape((image.height, image.width, 3))
        else:
            raise ValueError(f"不支持的颜色格式: {image.color_format}")
    else:
        raise ValueError(f"不支持的编码格式: {image.encoding}")
    
    return img

try:
    # 获取一帧图像
    img = camera.get_latest_image(cam_type, 1000.0)

    if img is not None:
        print(f"拍摄成功：{img.width}x{img.height}")

        # 创建保存目录
        os.makedirs("images", exist_ok=True)
        
        # 1. 保存原始图片
        raw_filename = f"images/head_color.jpg"
        with open(raw_filename, "wb") as f:
            f.write(img.data)
        print(f"原始图片已保存：{raw_filename}")

        # 2. 解码图像为YOLO可处理的格式
        cv_img = decode_camera_image(img)
        
        # 3. YOLO目标检测
        results = model(cv_img)
        
        # 4. 保存检测结果图片（带标注框）
        result_filename = "images/result.jpg"
        results[0].save(result_filename)
        print(f"检测结果图片已保存：{result_filename}")
        
        # 可选：打印检测到的目标信息
        print("\n检测到的目标：")
        for r in results:
            for box in r.boxes:
                cls_name = model.names[int(box.cls[0])]
                conf = float(box.conf[0])
                print(f"  - {cls_name} (置信度: {conf:.2f})")
    else:
        print("未获取到图像")

except Exception as e:
    print(f"程序出错：{e}")

finally:
    camera.close_camera()
    print("相机已关闭")