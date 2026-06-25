#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全身运动客户端 — 连接 9999 端口，发送 JSON 文件路径，
等待收到 "done\n" 后退出。

用法:
  python yolo/move_whole_body_client.py /path/to/your.json
"""

import sys
import json
import socket

HOST = "127.0.0.1"
PORT = 9999


def main():
    if len(sys.argv) < 2:
        print("用法: python yolo/move_whole_body_client.py <json文件路径>")
        sys.exit(1)

    json_path = sys.argv[1]

    print(f"🔗 连接 {HOST}:{PORT} ...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    # 发送 JSON 报文
    request = {"cmd": "move_whole_body", "path": json_path}
    sock.sendall((json.dumps(request) + "\n").encode("utf-8"))
    print(f"✅ 已发送: {request}")

    print("⏳ 等待运动完成...")
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
