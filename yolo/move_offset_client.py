#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
末端偏移客户端 — 连接 9999 端口，发送 move_offset 命令，
等待收到 move_offset_done 后退出。

用法:
  python yolo/move_offset_client.py '{"left":{"x":0,"y":0,"z":0},"right":{"x":0,"y":0,"z":0.01}}'
"""

import sys
import json
import socket

HOST = "127.0.0.1"
PORT = 9999


def main():
    if len(sys.argv) < 2:
        print('用法: python yolo/move_offset_client.py \'{"left":{"x":0,"y":0,"z":0},"right":{"x":0,"y":0,"z":0.01}}\'')
        sys.exit(1)

    offsets = json.loads(sys.argv[1])
    request = {
        "cmd": "move_offset",
        "left": offsets.get("left", {"x": 0, "y": 0, "z": 0}),
        "right": offsets.get("right", {"x": 0, "y": 0, "z": 0}),
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
