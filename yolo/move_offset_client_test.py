#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
末端偏移测试客户端 — 连接 9999 端口，
发送 move_offset 命令（右臂 Z 上升 0.03），
等待收到 move_offset_done 后退出。
"""

import json
import socket

HOST = "127.0.0.1"
PORT = 9999


def main():
    request = {
        "cmd": "move_offset",
        "left": {"x": 0, "y": 0, "z": 0},
        "right": {"x": 0, "y": 0, "z": 0.03},
    }

    print(f"🔗 连接 {HOST}:{PORT} ...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    sock.sendall((json.dumps(request) + "\n").encode("utf-8"))
    print(f"✅ 已发送: {request}")

    print("⏳ 等待末端偏移完成...")
    data = b""
    while b"\n" not in data:
        chunk = sock.recv(1024)
        if not chunk:
            break
        data += chunk

    response = json.loads(data.decode("utf-8").strip())
    print(f"📨 收到回复: {response}")

    sock.close()
    print("🏁 程序退出")


if __name__ == "__main__":
    main()
