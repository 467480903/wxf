#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT workspace version of cam_get_head_send.py.

The original /data/wxf/wxf/yolo/cam_get_head_send.py captures the head camera
through agibot_gdk and then sends RGB/depth to the external YOLO TCP service.
In this MQTT workspace, the previous step cam_get_head.py already captures the
same files through the Gateway HTTP camera endpoints:

    head.jpg
    head_depth.raw
    head_depth.jpg

This script therefore keeps the updated onsite flow and TCP protocol, but avoids
importing agibot_gdk inside yolo-env/bin/python, where GDK is not available.
"""

from __future__ import annotations

import base64
import json
import socket
import sys
from pathlib import Path

TCP_HOST = "192.168.57.164"
TCP_PORT = 9998
MODEL_NAME = sys.argv[1] if len(sys.argv) > 1 else "shelf.pt"
RGB_FILE = Path("head.jpg")
DEPTH_FILE = Path("head_depth.raw")
RESPONSE_FILE = Path("yyolo_depth_result.json")
COMPAT_RESPONSE_FILE = Path("yolo_depth_result.json")


def read_required(path: Path) -> bytes:
    if not path.exists():
        raise FileNotFoundError(f"required camera file not found: {path}")
    data = path.read_bytes()
    if not data:
        raise RuntimeError(f"required camera file is empty: {path}")
    print(f"read {path}: {len(data)} bytes", flush=True)
    return data


def main() -> int:
    color_bytes = read_required(RGB_FILE)
    depth_bytes = read_required(DEPTH_FILE)

    payload = {
        "cmd": "detect",
        "rgb": base64.b64encode(color_bytes).decode("ascii"),
        "depth": base64.b64encode(depth_bytes).decode("ascii"),
        "model": MODEL_NAME,
    }
    message = json.dumps(payload, ensure_ascii=False) + "\n"
    print(
        f"send detect request: host={TCP_HOST} port={TCP_PORT} "
        f"rgb_b64={len(payload['rgb'])} depth_b64={len(payload['depth'])} model={MODEL_NAME}",
        flush=True,
    )

    received = b""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(60.0)
        print(f"connect {TCP_HOST}:{TCP_PORT}", flush=True)
        sock.connect((TCP_HOST, TCP_PORT))
        print("connected, sending request", flush=True)
        sock.sendall(message.encode("utf-8"))
        print("request sent, waiting response", flush=True)
        while True:
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                print("receive timeout, stop receiving", flush=True)
                break
            if not chunk:
                break
            received += chunk

    if not received:
        raise RuntimeError("YOLO TCP service returned empty response")

    print(f"received response: {len(received)} bytes", flush=True)
    try:
        response_text = received.decode("utf-8")
        response_json = json.loads(response_text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        RESPONSE_FILE.write_bytes(received)
        print(f"response is not JSON ({exc}); saved raw to {RESPONSE_FILE}", flush=True)
        return 1

    RESPONSE_FILE.write_text(json.dumps(response_json, ensure_ascii=False, indent=2), encoding="utf-8")
    # Keep a compatibility copy because the existing correction/offset scripts
    # historically read yolo_depth_result.json.
    COMPAT_RESPONSE_FILE.write_text(json.dumps(response_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved response to {RESPONSE_FILE} and {COMPAT_RESPONSE_FILE}", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
