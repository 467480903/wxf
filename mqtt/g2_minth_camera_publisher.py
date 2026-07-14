#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G2 相机数据发布程序

持续读取 4 个相机数据，按 base64 编码后发布到 MQTT topic /G2_minth_cameras

相机：
  - 头部彩色 (kHeadColor)
  - 头部深度 (kHeadDepth)         → 转伪彩色后 JPEG 编码
  - 左手腕彩色 (kHandLeftColor)
  - 右手腕彩色 (kHandRightColor)

控制 topic：/G2_minth_camera
  - {"cmd": "start"}  开始发布
  - {"cmd": "stop"}   停止发布（线程仍以 0.5s 周期运行）

发布格式（/G2_minth_cameras）：
{
  "timestamp": 1782975716895377276,
  "head_color": "<base64 jpeg>",
  "head_depth": "<base64 jpeg>",
  "left_wrist": "<base64 jpeg>",
  "right_wrist": "<base64 jpeg>"
}
"""

import sys
import time
import json
import base64

import agibot_gdk
import paho.mqtt.client as mqtt

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

# ── 配置 ───────────────────────────────────────────────────
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

CAMERAS_TOPIC   = "/G2_minth_cameras"   # 发布相机数据
CONTROL_TOPIC   = "/G2_minth_camera"    # 接收 start/stop 控制
MQTT_CLIENT_ID  = "g2_camera_publisher"

# 采集周期（秒）— 线程始终按此周期运行
LOOP_INTERVAL = 0.5

# 4 个相机
CAMERA_LIST = [
    ("head_color", agibot_gdk.CameraType.kHeadColor,     "头部彩色"),
    ("head_depth", agibot_gdk.CameraType.kHeadDepth,     "头部深度"),
    ("left_wrist", agibot_gdk.CameraType.kHandLeftColor, "左手腕"),
    ("right_wrist",agibot_gdk.CameraType.kHandRightColor,"右手腕"),
]

# JPEG 编码质量
JPEG_QUALITY = 60


# ═══════════════════════════════════════════════════════════
#  图像编码
# ═══════════════════════════════════════════════════════════

def encode_image(image, key):
    """把 GDK Image 编码为 base64 字符串"""
    if image is None or not hasattr(image, 'data') or image.data is None:
        return None

    raw = image.data
    # 判断是否已经是压缩格式（JPEG/PNG），可直接 base64
    encoding = getattr(image, 'encoding', None)
    if encoding == agibot_gdk.Encoding.JPEG:
        return base64.b64encode(bytes(raw)).decode("ascii")
    if encoding == agibot_gdk.Encoding.PNG:
        return base64.b64encode(bytes(raw)).decode("ascii")

    # 未压缩数据，需要用 cv2 重新编码为 JPEG
    if not HAS_CV2:
        # 没有 cv2 时，尝试直接 base64（可能无法显示，但至少不崩）
        return base64.b64encode(bytes(raw)).decode("ascii")

    try:
        color_format = getattr(image, 'color_format', None)

        if key == "head_depth":
            # 深度图：16位数据（512000 = 400*640*2 字节）
            # 优先按 uint16 解析
            if len(raw) == image.width * image.height * 2:
                depth = np.frombuffer(raw, dtype=np.uint16).reshape((image.height, image.width))
            elif len(raw) == image.width * image.height:
                depth = np.frombuffer(raw, dtype=np.uint8).reshape((image.height, image.width))
            else:
                # 尝试 uint16
                depth = np.frombuffer(raw, dtype=np.uint16)
                if depth.size == image.width * image.height:
                    depth = depth.reshape((image.height, image.width))
                else:
                    print(f"  [深度] 数据大小 {len(raw)} 无法匹配 {image.width}x{image.height}")
                    return None

            # 归一化到 0-255
            valid = depth > 0
            if np.any(valid):
                mn, mx = depth[valid].min(), depth[valid].max()
                if mx > mn:
                    norm = ((depth.astype(np.float32) - mn) / (mx - mn) * 255).astype(np.uint8)
                else:
                    norm = np.zeros_like(depth, dtype=np.uint8)
            else:
                norm = np.zeros_like(depth, dtype=np.uint8)
            colored = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
        else:
            nparr = np.frombuffer(raw, dtype=np.uint8)
            if color_format == agibot_gdk.ColorFormat.RGB:
                img = nparr.reshape((image.height, image.width, 3))
                colored = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            elif color_format == agibot_gdk.ColorFormat.BGR:
                colored = nparr.reshape((image.height, image.width, 3))
            elif color_format == agibot_gdk.ColorFormat.GRAY8:
                gray = nparr.reshape((image.height, image.width))
                colored = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            else:
                colored = nparr.reshape((image.height, image.width, 3))

        ok, buf = cv2.imencode('.jpg', colored, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        if ok:
            return base64.b64encode(buf).decode("ascii")
    except Exception as e:
        print(f"[编码失败] {key}: {e}")

    return None


# ═══════════════════════════════════════════════════════════
#  主程序
# ═══════════════════════════════════════════════════════════

def main():
    print("#" * 60)
    print("#   G2 相机数据发布程序 - 启动   #")
    print("#" * 60)
    print(f"发布 topic : {CAMERAS_TOPIC}")
    print(f"控制 topic : {CONTROL_TOPIC}")
    print(f"采集周期   : {LOOP_INTERVAL}s")
    print(f"OpenCV     : {'已加载' if HAS_CV2 else '未加载（深度图可能无法显示）'}")
    print()

    # ── 初始化 GDK ──
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK 初始化失败")
        sys.exit(1)
    print("✅ GDK 初始化成功")

    camera = agibot_gdk.Camera()
    print("✅ Camera 对象创建完成，等待 DDS 连接...")
    time.sleep(3)

    # 发布开关：收到 start 才发布，收到 stop 暂停（线程继续跑）
    publishing = [False]

    # ── 初始化 MQTT ──
    mqtt_client = mqtt.Client(
        client_id=MQTT_CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            cmd = payload.get("cmd", "").lower()
            if cmd == "start":
                publishing[0] = True
                print("[控制] ▶️ 开始发布")
            elif cmd == "stop":
                publishing[0] = False
                print("[控制] ⏸️ 停止发布")
            else:
                print(f"[控制] 未知命令: {cmd}")
        except Exception as e:
            print(f"[控制] 解析失败: {e}")

    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    mqtt_client.subscribe(CONTROL_TOPIC, qos=0)
    mqtt_client.loop_start()
    print(f"[MQTT] 已连接到 {MQTT_BROKER}:{MQTT_PORT}")
    print("[提示] 默认不发布，等待 start 命令")

    try:
        while True:
            t0 = time.time()
            if publishing[0]:
                try:
                    msg = {"timestamp": int(time.time() * 1e9)}
                    for key, cam_type, cam_name in CAMERA_LIST:
                        try:
                            img = camera.get_latest_image(cam_type, 1000.0)
                            b64 = encode_image(img, key) if img is not None else None
                        except Exception as e:
                            b64 = None
                            print(f"  [{cam_name}] 读取异常: {e}")
                        if b64:
                            msg[key] = b64
                            print(f"  [{cam_name}] OK len={len(b64)}")
                        else:
                            print(f"  [{cam_name}] 无数据")

                    payload = json.dumps(msg, ensure_ascii=False)
                    mqtt_client.publish(CAMERAS_TOPIC, payload, qos=0)
                    print(f"[发布] payload={len(payload)} 字节")
                except Exception as e:
                    print(f"[错误] {e}")
            else:
                # 停止状态，仅心跳打印
                pass

            # 保持周期
            elapsed = time.time() - t0
            if elapsed < LOOP_INTERVAL:
                time.sleep(LOOP_INTERVAL - elapsed)
    except KeyboardInterrupt:
        print("\n[退出] 用户中断")
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        try:
            camera.close_camera()
        except Exception:
            pass
        if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
            print("⚠️ GDK 释放失败")
        else:
            print("✅ GDK 释放成功")
        print("🏁 程序结束")


if __name__ == "__main__":
    main()
