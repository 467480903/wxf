#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G2 数据读写服务程序

专门处理数据持久化操作，与 app_service 解耦。

监听 topic：
  - /G2_minth_save_joints    : 保存关节角到 datas/joints/{type}/{name}.json
  - /G2_minth_save_position  : 保存末端位姿到 datas/positions/{type}/{name}.json

消息格式：
  保存关节角：
    {"cmd": "save_joints", "type": "WBC", "name": "hold",
     "data": {"idx11_head_joint1": 0.1, ...}}

  保存末端位姿：
    {"cmd": "save_position", "type": "left", "name": "pick",
     "data": {"x": 0.1, "y": 0.2, "z": 0.3, "rx": 0, "ry": 0, "rz": 0}}
    type 可选: left / right / both
      - both 时 data 包含 left 和 right 两个子对象
"""

import os
import sys
import json
import time

import paho.mqtt.client as mqtt

# ── 路径配置 ───────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
JOINTS_DIR = os.path.join(PROJECT_DIR, "datas", "joints")
POSITIONS_DIR = os.path.join(PROJECT_DIR, "datas", "positions")

# ── MQTT 配置 ─────────────────────────────────────────────
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "g2_data_service"

TOPIC_SAVE_JOINTS = "/G2_minth_save_joints"
TOPIC_SAVE_POSITION = "/G2_minth_save_position"


# ═══════════════════════════════════════════════════════════
#  保存接口
# ═══════════════════════════════════════════════════════════

def save_joints(msg):
    """保存关节角
    msg: {"type": "WBC", "name": "hold", "data": {关节名: 弧度}}
    """
    save_type = msg.get("type", "WBC")
    save_name = msg.get("name", "unnamed")
    joints = msg.get("data", {})
    if not isinstance(joints, dict):
        print(f"  ❌ data 不是字典: {type(joints)}")
        return

    save_dir = os.path.join(JOINTS_DIR, save_type)
    os.makedirs(save_dir, exist_ok=True)

    json_name = save_name if save_name.endswith('.json') else save_name + '.json'
    json_path = os.path.join(save_dir, json_name)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(joints, f, ensure_ascii=False, indent=2)

    print(f"  ✅ 关节角已保存: {json_path} ({len(joints)} 个关节)")


def save_position(msg):
    """保存末端位姿
    msg: {"type": "left"/"right"/"both", "name": "pick",
          "data": {"x":0.1, "y":0.2, "z":0.3, "rx":0, "ry":0, "rz":0}}
    both 时 data = {"left": {...}, "right": {...}}
    """
    save_type = msg.get("type", "both")
    save_name = msg.get("name", "unnamed")
    pos_data = msg.get("data", {})
    if not isinstance(pos_data, dict):
        print(f"  ❌ data 不是字典: {type(pos_data)}")
        return

    save_dir = os.path.join(POSITIONS_DIR, save_type)
    os.makedirs(save_dir, exist_ok=True)

    json_name = save_name if save_name.endswith('.json') else save_name + '.json'
    json_path = os.path.join(save_dir, json_name)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(pos_data, f, ensure_ascii=False, indent=2)

    print(f"  ✅ 末端位姿已保存: {json_path}")


# ═══════════════════════════════════════════════════════════
#  MQTT
# ═══════════════════════════════════════════════════════════

# 命令分发表
CMD_HANDLERS = {
    "save_joints":   save_joints,
    "save_position": save_position,
}


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[MQTT] 已连接到 {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(TOPIC_SAVE_JOINTS, qos=0)
        client.subscribe(TOPIC_SAVE_POSITION, qos=0)
        print(f"[MQTT] 已订阅: {TOPIC_SAVE_JOINTS}, {TOPIC_SAVE_POSITION}")
        print("-" * 60)
    else:
        print(f"[MQTT] 连接失败，返回码: {rc}")


def on_message(client, userdata, msg):
    """收到 MQTT 消息时分发命令"""
    try:
        payload = msg.payload.decode("utf-8")
        cmd_msg = json.loads(payload)
        cmd = cmd_msg.get("cmd")
    except Exception as e:
        print(f"[解析失败] {e}，原始: {msg.payload}")
        return

    print(f"\n{'=' * 60}")
    print(f"[收到命令] topic={msg.topic}, cmd={cmd}")
    print(f"{'=' * 60}")

    handler = CMD_HANDLERS.get(cmd)
    if handler is None:
        print(f"⚠️ 未知命令: {cmd}，支持的命令: {list(CMD_HANDLERS.keys())}")
        return

    try:
        handler(cmd_msg)
    except Exception as e:
        print(f"❌ 命令执行异常: {e}")
    print(f"{'─' * 60}\n")


# ═══════════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════════

def main():
    print("#" * 60)
    print("#   G2 数据读写服务 - 启动   #")
    print("#" * 60)
    print(f"joints 目录    : {JOINTS_DIR}")
    print(f"positions 目录 : {POSITIONS_DIR}")
    print(f"save_joints topic   : {TOPIC_SAVE_JOINTS}")
    print(f"save_position topic : {TOPIC_SAVE_POSITION}")
    print(f"支持命令: {list(CMD_HANDLERS.keys())}")
    print()

    # 确保目录存在
    os.makedirs(JOINTS_DIR, exist_ok=True)
    os.makedirs(POSITIONS_DIR, exist_ok=True)

    client = mqtt.Client(
        client_id=MQTT_CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        print(f"[MQTT] 正在连接 {MQTT_BROKER}:{MQTT_PORT} ...")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[退出] 用户中断")
    except Exception as e:
        print(f"[错误] {e}")
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
        print("🏁 程序结束")


if __name__ == "__main__":
    main()
