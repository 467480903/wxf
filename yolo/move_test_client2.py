#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试客户端 — 连接 9999 端口，发送 JSON 文件路径，
等待收到 "done\n" 后退出。
"""

import sys
import socket

HOST = "127.0.0.1"
PORT = 9999

DEFAULT_JSON_PATH = "/data/wxf/wxf/positions/pick_standby.json"


def main():
    json_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_JSON_PATH

    print(f"🔗 连接 {HOST}:{PORT} ...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    print(f"✅ 已连接，发送文件路径: {json_path}")

    sock.sendall((json_path + "\n").encode("utf-8"))

    print("⏳ 等待运动完成...")
    data = b""
    while b"\n" not in data:
        chunk = sock.recv(1024)
        if not chunk:
            break
        data += chunk

    response = data.decode("utf-8").strip()
    print(f"📨 收到回复: {response}")

    sock.close()
    print("🏁 程序退出")


if __name__ == "__main__":
    main()
