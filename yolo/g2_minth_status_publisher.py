#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G2 状态读取程序

持续读取机器人所有关节角和左右手末端坐标，发布到 MQTT topic /G2_minth_status

发布内容为 JSON，格式：
{
  "timestamp": "2026-07-14 15:00:00",
  "joints": {
      "idx01_body_joint1": 0.123,
      ...
  },
  "left_ee": {
      "position": [x, y, z],
      "orientation": [x, y, z, w]
  },
  "right_ee": {
      "position": [x, y, z],
      "orientation": [x, y, z, w]
  }
}
"""

import sys
import os
import time
import json

import agibot_gdk
import paho.mqtt.client as mqtt

# ── 配置 ───────────────────────────────────────────────────
LEFT_NAME = "arm_l_end_link"
RIGHT_NAME = "arm_r_end_link"

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "/G2_minth_status"
MQTT_CLIENT_ID = "g2_status_publisher"

# 发布周期（秒）
PUBLISH_INTERVAL = 0.5


# ═══════════════════════════════════════════════════════════
#  状态读取
# ═══════════════════════════════════════════════════════════

def read_joint_states(robot):
    """读取所有关节状态，返回 {关节名: 位置} 字典"""
    joint_states = robot.get_joint_states()
    joints = {}
    for state in joint_states['states']:
        joints[state['name']] = round(state['motor_position'], 6)
    return joints


def find_pose_by_name(status, target_name):
    """从 motion_control_status 中按名称查找末端位姿"""
    for i, frame_name in enumerate(status.frame_names):
        if frame_name == target_name:
            pose = status.frame_poses[i]
            return {
                "position": [
                    round(pose.position.x, 6),
                    round(pose.position.y, 6),
                    round(pose.position.z, 6),
                ],
                "orientation": [
                    round(pose.orientation.x, 6),
                    round(pose.orientation.y, 6),
                    round(pose.orientation.z, 6),
                    round(pose.orientation.w, 6),
                ],
            }
    return None


def read_end_effector_poses(robot):
    """读取左右手末端坐标"""
    status = robot.get_motion_control_status()
    left = find_pose_by_name(status, LEFT_NAME)
    right = find_pose_by_name(status, RIGHT_NAME)
    return left, right


def build_status_message(robot):
    """构建状态 JSON 消息"""
    joints = read_joint_states(robot)
    left_ee, right_ee = read_end_effector_poses(robot)
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "joints": joints,
        "left_ee": left_ee,
        "right_ee": right_ee,
    }


# ═══════════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════════

def main():
    print("#" * 60)
    print("#   G2 状态读取程序 - 启动   #")
    print("#" * 60)
    print(f"发布 topic : {MQTT_TOPIC}")
    print(f"发布周期   : {PUBLISH_INTERVAL}s")
    print()

    # ── 初始化 GDK ──
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK 初始化失败")
        sys.exit(1)
    print("✅ GDK 初始化成功")

    robot = agibot_gdk.Robot()
    time.sleep(2)

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
                msg = build_status_message(robot)
                payload = json.dumps(msg, ensure_ascii=False)
                mqtt_client.publish(MQTT_TOPIC, payload, qos=0)
                print(f"[发布] joints={len(msg['joints'])}个, "
                      f"left_ee={'有' if msg['left_ee'] else '无'}, "
                      f"right_ee={'有' if msg['right_ee'] else '无'}")
            except Exception as e:
                print(f"[错误] 读取/发布失败: {e}")
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
