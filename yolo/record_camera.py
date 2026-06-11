#!/usr/bin/env python3
"""
监听头部 RGB 相机视频输入，每隔 0.5 秒保存一张图片到 yolo/images 文件夹内
"""

import time
import os
import threading
import agibot_gdk

# ================= 配置 =================
SAVE_INTERVAL = 0.5          # 保存间隔（秒）
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")


def ensure_dir(path):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)


def record_loop(camera, cam_type):
    """循环采集并保存图片"""
    frame_count = 0
    print(f"🟢 开始录制，每 {SAVE_INTERVAL} 秒保存一张图片...")
    print(f"📂 保存路径: {IMAGES_DIR}")
    print("按 Ctrl+C 停止录制\n")

    try:
        while True:
            # 获取最新一帧图像（超时设为 1 秒）
            img = camera.get_latest_image(cam_type, 1000.0)

            if img is not None:
                frame_count += 1
                # 时间戳命名
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"head_color_{timestamp}.jpg"
                filepath = os.path.join(IMAGES_DIR, filename)

                with open(filepath, "wb") as f:
                    f.write(img.data)

                print(f"[{frame_count}] ✅ 已保存: {filename} ({img.width}x{img.height})")
            else:
                print("⚠️ 未获取到图像帧")

            time.sleep(SAVE_INTERVAL)

    except KeyboardInterrupt:
        print("\n🛑 用户中断，停止录制...")
    except Exception as e:
        print(f"❌ 录制出错: {e}")
    finally:
        print(f"📊 共保存 {frame_count} 张图片")


def main():
    # 确保 images 目录存在
    ensure_dir(IMAGES_DIR)

    # 初始化相机
    print("🔄 初始化相机...")
    camera = agibot_gdk.Camera()
    time.sleep(2)  # 等待相机初始化

    # 使用头部彩色相机
    cam_type = agibot_gdk.CameraType.kHeadColor

    try:
        record_loop(camera, cam_type)
    finally:
        camera.close_camera()
        print("🔒 相机已关闭")


if __name__ == "__main__":
    main()
