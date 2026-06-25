#!/usr/bin/env python3
"""
拍摄 头部彩色相机 + 头部深度相机，保存彩色图和深度图（原始 uint16 + 伪彩色），
并通过 TCP 发送给 YOLO 检测服务（192.168.57.164:9998），
接收检测结果并保存为 yolo_response.json

报文格式：
    {"cmd": "detect", "rgb": "base64...", "depth": "base64...", "model": "holes.pt"}
"""

import sys
import time
import os
import json
import socket
import base64
import numpy as np
import agibot_gdk

# ========== TCP 配置 ==========
TCP_HOST = "192.168.57.164"
TCP_PORT = 9998
MODEL_NAME = sys.argv[1] if len(sys.argv) > 1 else "shelf.pt"
RESPONSE_FILE = "yyolo_depth_result.json"

# ========== 初始化相机 ==========
camera = agibot_gdk.Camera()
time.sleep(2)

os.makedirs("images", exist_ok=True)

color_bytes = None
depth_bytes = None

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
        color_bytes = color_img.data
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
        depth_bytes = depth_img.data

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

# ========== 3. 通过 TCP 发送图片并接收检测结果 ==========
if color_bytes is None or depth_bytes is None:
    print("⚠️ 彩色图或深度图未获取到，跳过 TCP 发送")
else:
    # base64 编码
    rgb_b64 = base64.b64encode(color_bytes).decode("ascii")
    depth_b64 = base64.b64encode(depth_bytes).decode("ascii")

    # 构造请求报文
    payload = {
        "cmd": "detect",
        "rgb": rgb_b64,
        "depth": depth_b64,
        "model": MODEL_NAME
    }
    message = json.dumps(payload, ensure_ascii=False) + "\n"
    print(f"📦 请求报文内容：{message}")
    print(f"   rgb 长度={len(rgb_b64)}, depth 长度={len(depth_b64)}, model={MODEL_NAME}")

    # TCP 连接并发送
    sock = None
    try:
        print(f"🔗 连接 {TCP_HOST}:{TCP_PORT} ...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(60.0)  # 接收超时 60 秒
        sock.connect((TCP_HOST, TCP_PORT))
        print("✅ 已连接，发送报文...")

        sock.sendall(message.encode("utf-8"))
        print("📨 报文已发送，等待回复...")

        # 接收回复（服务端发送完毕后关闭连接即结束）
        received = b""
        while True:
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                print("⚠️ 接收超时，停止接收")
                break
            if not chunk:
                # 连接已被对端关闭
                break
            received += chunk

        if not received:
            print("⚠️ 未收到任何回复")
        else:
            print(f"📨 收到回复，长度={len(received)} 字节")
            # 保存为 yolo_response.json
            try:
                response_text = received.decode("utf-8")
                response_json = json.loads(response_text)
                with open(RESPONSE_FILE, "w", encoding="utf-8") as f:
                    json.dump(response_json, f, ensure_ascii=False, indent=2)
                print(f"✅ 回复已保存为 {RESPONSE_FILE}")
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                # 回复不是合法 JSON，原样写入
                print(f"⚠️ 回复非合法 JSON（{e}），原样保存二进制内容")
                with open(RESPONSE_FILE, "wb") as f:
                    f.write(received)
                print(f"✅ 回复已保存为 {RESPONSE_FILE}")

    except Exception as e:
        print(f"❌ TCP 通信失败：{e}")
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass

print("🏁 程序结束")
