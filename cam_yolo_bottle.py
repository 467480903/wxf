#!/usr/bin/env python3
"""
仅拍摄1张头部彩色相机图片 + YOLO检测第一个矿泉水瓶 + 保存坐标到JSON文本
"""

import time
import os
import json
import agibot_gdk
import numpy as np
import cv2
from ultralytics import YOLO

# 矿泉水瓶在COCO数据集中的类别ID
WATER_BOTTLE_CLASS_ID = 39
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

def save_first_bottle_coordinate(bottle_data, save_path="images/first_bottle_coordinate.json"):
    """将第一个矿泉水瓶坐标保存为JSON格式文本文件"""
    # 构造完整的JSON数据结构
    json_data = {
        "timestamp": int(time.time()),
        "image_info": {
            "width": img.width if 'img' in locals() else 0,
            "height": img.height if 'img' in locals() else 0
        },
        "first_bottle": bottle_data
    }
    
    # 确保目录存在
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # 写入JSON文件（格式化输出，便于阅读和解析）
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
    
    print(f"\n第一个矿泉水瓶坐标已保存到：{save_path}")

try:
    # 1. 获取相机图像
    img = camera.get_latest_image(cam_type, 1000.0)

    if img is not None:
        print(f"拍摄成功：{img.width}x{img.height}")

        # 创建保存目录
        os.makedirs("images", exist_ok=True)
        
        # 2. 保存原始图片
        raw_filename = f"images/head_color.jpg"
        with open(raw_filename, "wb") as f:
            f.write(img.data)
        print(f"原始图片已保存：{raw_filename}")

        # 3. 解码图像为YOLO可处理的格式
        cv_img = decode_camera_image(img)
        
        # 4. YOLO目标检测（筛选矿泉水瓶）
        results = model(cv_img)
        
        # 存储第一个矿泉水瓶的数据
        first_bottle = None
        
        # 遍历检测结果，找到第一个矿泉水瓶
        for r in results:
            for box in r.boxes:
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                if class_id == WATER_BOTTLE_CLASS_ID or class_name.lower() == "bottle":
                    # 获取边界框坐标（x1,y1:左上角；x2,y2:右下角）
                    x1, y1, x2, y2 = map(float, box.xyxy[0])
                    # 计算中心点坐标
                    center_x = round((x1 + x2) / 2, 2)
                    center_y = round((y1 + y2) / 2, 2)
                    # 计算宽高
                    width = round(x2 - x1, 2)
                    height = round(y2 - y1, 2)
                    # 置信度
                    confidence = round(float(box.conf[0]), 2)
                    
                    # 构造第一个瓶子的数据（只取第一个）
                    first_bottle = {
                        "bbox": {  # 边界框坐标（左上角/右下角）
                            "x1": round(x1, 2),
                            "y1": round(y1, 2),
                            "x2": round(x2, 2),
                            "y2": round(y2, 2)
                        },
                        "center": {  # 中心点坐标
                            "x": center_x,
                            "y": center_y
                        },
                        "size": {  # 瓶子框的宽高
                            "width": width,
                            "height": height
                        },
                        "confidence": confidence  # 检测置信度
                    }
                    # 找到第一个后立即退出循环
                    break
            # 找到第一个后退出外层循环
            if first_bottle is not None:
                break
        
        # 5. 保存检测结果图片（带标注框）
        result_filename = "images/result.jpg"
        results[0].save(result_filename)
        print(f"检测结果图片已保存：{result_filename}")
        
        # 6. 输出并保存第一个矿泉水瓶坐标
        if first_bottle is not None:
            print("\n检测到第一个矿泉水瓶，坐标信息：")
            print(f"  边界框（x1,y1,x2,y2）: {first_bottle['bbox']['x1']}, {first_bottle['bbox']['y1']}, {first_bottle['bbox']['x2']}, {first_bottle['bbox']['y2']}")
            print(f"  中心点（x,y）: {first_bottle['center']['x']}, {first_bottle['center']['y']}")
            print(f"  置信度: {first_bottle['confidence']}")
            
            # 保存到JSON文件
            save_first_bottle_coordinate(first_bottle)
        else:
            print("\n未检测到矿泉水瓶")
            # 保存空数据到JSON
            save_first_bottle_coordinate({"status": "未检测到矿泉水瓶"})
    else:
        print("未获取到图像")

except Exception as e:
    print(f"程序出错：{e}")

finally:
    # 确保相机关闭
    camera.close_camera()
    print("相机已关闭")