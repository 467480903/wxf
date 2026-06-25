#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全身关节控制服务 — 监听 TCP 9999 端口，
接收 client 发来的 JSON 文件绝对路径，
读取文件并执行关节运动，完成后回复 "done\n"。
"""

import os
import time
import json
import socket
import threading
import agibot_gdk

from move_whole_body_by_json import (
    HEAD_JOINT_KEYS,
    WAIST_JOINT_KEYS,
    LEFT_ARM_JOINT_KEYS,
    RIGHT_ARM_JOINT_KEYS,
    HEAD_SPEED,
    WAIST_SPEED,
    ARM_SPEED,
    extract_positions,
)

HOST = "0.0.0.0"
PORT = 9999

# ── 初始化 GDK（服务启动时一次性初始化）──
print("🔄 初始化 GDK...")
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("❌ GDK 初始化失败")
    exit(1)
print("✅ GDK 初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)


def move_sequentially(data):
    """顺序控制：头部 → 腰部 → 手臂"""
    head_pos = extract_positions(data, HEAD_JOINT_KEYS)
    head_vel = [HEAD_SPEED] * len(head_pos)
    print(f"🔹 头部  →  {[f'{p:.3f}' for p in head_pos]}")
    try:
        robot.move_head_joint(head_pos, head_vel)
    except Exception as e:
        print(f"   ❌ 头部控制失败: {e}")
    time.sleep(0.2)

    waist_pos = extract_positions(data, WAIST_JOINT_KEYS)
    waist_vel = [WAIST_SPEED] * len(waist_pos)
    print(f"🔹 腰部  →  {[f'{p:.3f}' for p in waist_pos]}")
    try:
        robot.move_waist_joint(waist_pos, waist_vel)
    except Exception as e:
        print(f"   ❌ 腰部控制失败: {e}")
    time.sleep(0.2)

    left_arm_pos = extract_positions(data, LEFT_ARM_JOINT_KEYS)
    right_arm_pos = extract_positions(data, RIGHT_ARM_JOINT_KEYS)
    arm_positions = left_arm_pos + right_arm_pos
    arm_velocities = [ARM_SPEED] * len(arm_positions)
    print(f"🔹 左臂  →  {[f'{p:.3f}' for p in left_arm_pos]}")
    print(f"🔹 右臂  →  {[f'{p:.3f}' for p in right_arm_pos]}")
    try:
        robot.move_arm_joint(arm_positions, arm_velocities, 2)
    except Exception as e:
        print(f"   ❌ 手臂控制失败: {e}")


def handle_client(conn, addr):
    """处理单个 client 连接"""
    print(f"\n📞 新连接: {addr}")
    try:
        # 接收 JSON 报文（以 \n 结尾）
        data = b""
        while b"\n" not in data:
            chunk = conn.recv(1024)
            if not chunk:
                break
            data += chunk

        request = json.loads(data.decode("utf-8").strip())
        print(f"📄 收到请求: {request}")

        if request.get("cmd") != "move_whole_body":
            print(f"❌ 未知命令: {request.get('cmd')}")
            conn.sendall((json.dumps({"cmd": "error", "msg": "unknown cmd"}) + "\n").encode("utf-8"))
            return

        file_path = request.get("path", "")
        print(f"📄 文件路径: {file_path}")

        if not os.path.exists(file_path):
            print(f"❌ 找不到文件: {file_path}")
            conn.sendall((json.dumps({"cmd": "error", "msg": "file not found"}) + "\n").encode("utf-8"))
            return

        # 读取 JSON
        with open(file_path, "r", encoding="utf-8") as f:
            pos_data = json.load(f)
        print(f"✅ JSON 读取成功: {file_path}")

        # 执行运动
        move_sequentially(pos_data)
        print("✅ 运动执行完成")

        # 回复 client
        response = {"cmd": "move_whole_body_done"}
        conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
        print(f"✅ 已回复 {response} 给 {addr}")

    except Exception as e:
        print(f"❌ 处理连接出错: {e}")
        try:
            conn.sendall((json.dumps({"cmd": "error", "msg": str(e)}) + "\n").encode("utf-8"))
        except Exception:
            pass
    finally:
        conn.close()
        print(f"🔌 连接关闭: {addr}")


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"🚀 服务启动，监听 {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server.accept()
            handle_client(conn, addr)
    except KeyboardInterrupt:
        print("\n⚠️  服务停止")
    finally:
        server.close()
        agibot_gdk.gdk_release()
        print("✅ GDK 已释放")


if __name__ == "__main__":
    main()
