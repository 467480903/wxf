#!/usr/bin/env python3
"""
周期性获取头部相机和右手相机图像并保存到 web 目录
"""

import time
import os
import agibot_gdk
import numpy as np
from typing import Optional

# 检查是否安装了 OpenCV
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

class HeadRightArmCamera:
    def __init__(self, web_dir="../web"):
        """初始化相机对象"""
        print("正在初始化相机对象...")
        self.camera = agibot_gdk.Camera()
        time.sleep(3)  # 给相机一些初始化时间
        
        # 相机类型定义
        self.head_camera_type = agibot_gdk.CameraType.kHeadColor
        self.right_hand_camera_type = agibot_gdk.CameraType.kHandRightColor
        
        # web 目录路径
        self.web_dir = web_dir
        os.makedirs(self.web_dir, exist_ok=True)
        
        print("相机初始化完成！")
    
    def decode_image_data(self, image) -> Optional[np.ndarray]:
        """解码图像数据为 numpy 数组"""
        if not hasattr(image, 'data') or not image.data.any():
            print("图像数据为空")
            return None
        
        try:
            if image.encoding == agibot_gdk.Encoding.JPEG:
                if HAS_OPENCV:
                    nparr = np.frombuffer(image.data, np.uint8)
                    decoded_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    return decoded_image
                else:
                    return image.data
                    
            elif image.encoding == agibot_gdk.Encoding.PNG:
                if HAS_OPENCV:
                    nparr = np.frombuffer(image.data, np.uint8)
                    decoded_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    return decoded_image
                else:
                    return image.data
                    
            elif image.encoding == agibot_gdk.Encoding.UNCOMPRESSED:
                if image.color_format == agibot_gdk.ColorFormat.RGB:
                    decoded_image = np.frombuffer(image.data, dtype=np.uint8)
                    decoded_image = decoded_image.reshape((image.height, image.width, 3))
                    if HAS_OPENCV:
                        decoded_image = cv2.cvtColor(decoded_image, cv2.COLOR_RGB2BGR)
                    return decoded_image
                elif image.color_format == agibot_gdk.ColorFormat.BGR:
                    decoded_image = np.frombuffer(image.data, dtype=np.uint8)
                    decoded_image = decoded_image.reshape((image.height, image.width, 3))
                    return decoded_image
                elif image.color_format == agibot_gdk.ColorFormat.GRAY8:
                    decoded_image = np.frombuffer(image.data, dtype=np.uint8)
                    decoded_image = decoded_image.reshape((image.height, image.width))
                    if HAS_OPENCV:
                        decoded_image = cv2.cvtColor(decoded_image, cv2.COLOR_GRAY2BGR)
                    return decoded_image
                else:
                    print(f"不支持的颜色格式: {image.color_format}")
                    return None
            else:
                print(f"不支持的编码格式: {image.encoding}")
                return None
                
        except Exception as e:
            print(f"解码图像数据失败: {e}")
            return None
    
    def save_image_to_web_dir(self, image, filename):
        """保存图像到 web 目录"""
        try:
            file_path = os.path.join(self.web_dir, filename)
            
            if image.encoding in [agibot_gdk.Encoding.JPEG, agibot_gdk.Encoding.PNG]:
                with open(file_path, "wb") as f:
                    f.write(image.data)
                print(f"图像已保存到: {file_path}")
                return True
            
            decoded_image = self.decode_image_data(image)
            if decoded_image is not None:
                if HAS_OPENCV:
                    cv2.imwrite(file_path, decoded_image)
                    print(f"图像已保存到: {file_path}")
                    return True
                else:
                    print("未安装 OpenCV，无法保存非 JPEG/PNG 格式的图像")
                    return False
            else:
                print(f"无法保存图像数据")
                return False
        except Exception as e:
            print(f"保存图像失败: {e}")
            return False
    
    def capture_and_save_images(self):
        """捕获并保存头部和右手相机图像"""
        try:
            # 获取头部相机图像
            head_image = self.camera.get_latest_image(self.head_camera_type, 1000.0)
            if head_image is not None:
                self.save_image_to_web_dir(head_image, "head.jpg")
            else:
                print("未收到头部相机图像")
            
            # 获取右手相机图像
            right_hand_image = self.camera.get_latest_image(self.right_hand_camera_type, 1000.0)
            if right_hand_image is not None:
                self.save_image_to_web_dir(right_hand_image, "right.jpg")
            else:
                print("未收到右手相机图像")
                
        except Exception as e:
            print(f"捕获和保存图像出错: {e}")
    
    def start_periodic_capture(self, interval=1.0):
        """开始周期性捕获图像
        
        Args:
            interval: 捕获间隔时间（秒），默认为1秒
        """
        print(f"开始周期性捕获图像，间隔: {interval}秒")
        print("按 Ctrl+C 停止")
        
        try:
            while True:
                self.capture_and_save_images()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n周期性捕获已停止")
        finally:
            try:
                self.camera.close_camera()
                print("相机已关闭")
            except Exception as e:
                print(f"关闭相机时出错: {e}")

def main():
    camera = HeadRightArmCamera()
    
    try:
        # 每0.5秒捕获一次图像
        camera.start_periodic_capture(interval=0.5)
    except Exception as e:
        print(f"程序运行出错: {e}")

if __name__ == "__main__":
    main()
