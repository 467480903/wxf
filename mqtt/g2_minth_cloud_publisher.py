#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G2 激光雷达点云发布程序

持续读取前部 + 后部激光雷达点云数据，降采样后通过 MQTT 发布到 /G2_minth_cloud

发布内容为 JSON，格式：
{
  "timestamp": 1782975716895377276,
  "count": 3000,
  "points": [[x,y,z], [x,y,z], ...],   // 前后雷达合并后降采样
  "front_count": 1500,
  "back_count": 1500
}
"""

import sys
import time
import json
import struct

import numpy as np
import agibot_gdk
import paho.mqtt.client as mqtt

# ── 配置 ───────────────────────────────────────────────────
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "/G2_minth_cloud"
MQTT_CLIENT_ID = "g2_cloud_publisher"

# 发布周期（秒）
PUBLISH_INTERVAL = 1

# 降采样间隔：每隔 N 个点取一个，控制数据量
DOWNSAMPLE_STEP = 4

# 过滤距离阈值（米），太远的点不发送
MAX_DISTANCE = 30.0

# 雷达类型
LIDAR_TYPES = [
    (agibot_gdk.LidarType.kLidarFront, "前部雷达"),
    (agibot_gdk.LidarType.kLidarBack,  "后部雷达"),
]


# ═══════════════════════════════════════════════════════════
#  点云解析
# ═══════════════════════════════════════════════════════════

def parse_pointcloud(pointcloud):
    """解析 PointCloud 为 (N, 4) numpy 数组 [x, y, z, intensity]"""
    if not hasattr(pointcloud, 'data'):
        return None

    try:
        if isinstance(pointcloud.data, np.ndarray):
            data = pointcloud.data.astype(np.uint8)
        else:
            data = np.frombuffer(pointcloud.data, dtype=np.uint8)

        if pointcloud.point_step <= 0:
            return None

        num_points = len(data) // pointcloud.point_step
        data = data[:num_points * pointcloud.point_step]
        data = data.reshape((num_points, pointcloud.point_step))

        # 提取 x, y, z, intensity 字段
        channels = []
        field_names = [f.name for f in pointcloud.fields]

        for field in pointcloud.fields:
            if field.name in ('x', 'y', 'z', 'intensity'):
                slc = data[:, field.offset:field.offset + 4]
                val = np.ascontiguousarray(slc).view(np.float32)
                channels.append((field.name, val))

        if len(channels) >= 3:
            # 按 x, y, z 顺序组装
            result = {}
            for name, arr in channels:
                result[name] = arr
            xs = result.get('x', np.zeros(num_points))
            ys = result.get('y', np.zeros(num_points))
            zs = result.get('z', np.zeros(num_points, dtype=np.float32))
            intens = result.get('intensity', np.zeros(num_points, dtype=np.float32))
            return np.column_stack([xs, ys, zs, intens])

        return None
    except Exception as e:
        print(f"[解析失败] {e}")
        return None


def build_cloud_message(lidar):
    """读取前后两个雷达点云，合并后构建 MQTT 消息"""
    all_points = []
    front_count = 0
    back_count = 0
    latest_ts = 0

    for lidar_type, lidar_name in LIDAR_TYPES:
        pointcloud = lidar.get_latest_pointcloud(lidar_type, 1000.0)
        if pointcloud is None:
            print(f"  [{lidar_name}] 未获取到数据")
            continue

        pts = parse_pointcloud(pointcloud)
        if pts is None or len(pts) == 0:
            print(f"  [{lidar_name}] 解析为空")
            continue

        # 距离过滤
        dist = np.sqrt(pts[:, 0] ** 2 + pts[:, 1] ** 2 + pts[:, 2] ** 2)
        mask = dist < MAX_DISTANCE
        pts = pts[mask]

        # 降采样
        pts = pts[::DOWNSAMPLE_STEP]

        count = len(pts)
        if lidar_type == agibot_gdk.LidarType.kLidarFront:
            front_count = count
        else:
            back_count = count

        # 转为列表
        for i in range(count):
            all_points.append([
                round(float(pts[i, 0]), 3),
                round(float(pts[i, 1]), 3),
                round(float(pts[i, 2]), 3),
            ])

        if pointcloud.timestamp_ns > latest_ts:
            latest_ts = pointcloud.timestamp_ns

        print(f"  [{lidar_name}] 原始={len(pts) * DOWNSAMPLE_STEP}, "
              f"过滤后={count}")

    if not all_points:
        return None

    return {
        "timestamp": latest_ts,
        "count": len(all_points),
        "front_count": front_count,
        "back_count": back_count,
        "points": all_points,
    }


# ═══════════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════════

def main():
    print("#" * 60)
    print("#   G2 激光雷达点云发布程序 - 启动   #")
    print("#" * 60)
    print(f"发布 topic : {MQTT_TOPIC}")
    print(f"发布周期   : {PUBLISH_INTERVAL}s")
    print(f"降采样间隔 : 每 {DOWNSAMPLE_STEP} 个点取 1 个")
    print(f"最大距离   : {MAX_DISTANCE} 米")
    print()

    # ── 初始化 GDK ──
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK 初始化失败")
        sys.exit(1)
    print("✅ GDK 初始化成功")

    lidar = agibot_gdk.Lidar()
    print("✅ Lidar 对象创建完成，等待 DDS 连接...")
    time.sleep(3)

    # ── 初始化 MQTT ──
    mqtt_client = mqtt.Client(
        client_id=MQTT_CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()
    print(f"[MQTT] 已连接到 {MQTT_BROKER}:{MQTT_PORT}")

    try:
        while True:
            try:
                msg = build_cloud_message(lidar)
                if msg is None:
                    print("[警告] 未获取到点云数据")
                else:
                    payload = json.dumps(msg, ensure_ascii=False)
                    mqtt_client.publish(MQTT_TOPIC, payload, qos=0)
                    print(f"[发布] 总点数={msg['count']}, "
                          f"前部={msg['front_count']}, "
                          f"后部={msg['back_count']}, "
                          f"payload={len(payload)} 字节")
            except Exception as e:
                print(f"[错误] {e}")
            time.sleep(PUBLISH_INTERVAL)
    except KeyboardInterrupt:
        print("\n[退出] 用户中断")
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
            print("⚠️ GDK 释放失败")
        else:
            print("✅ GDK 释放成功")
        print("🏁 程序结束")


if __name__ == "__main__":
    main()
