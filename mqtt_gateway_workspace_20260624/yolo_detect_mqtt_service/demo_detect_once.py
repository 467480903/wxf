#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal customer-script demo for calling YOLO Detect through MQTT.

Run:

    cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo_detect_mqtt_service
    ./demo_detect_once.py

What this demo does:

1. It does not import GDK.
2. It asks Gateway HTTP for one RGB frame and one raw depth frame.
3. It sends both frames to the always-on MQTT YOLO service.
4. It prints the fields most scripts usually need.

If this works, a customer script can copy the `detect_once()` call below and use
the returned dictionary directly.
"""
from __future__ import annotations

import json

from yolo_detect_gateway_client import detect_once


def main() -> int:
    result = detect_once(
        # Gateway and MQTT are both local on the robot by default. These values
        # are written explicitly here so the customer can see what is being used.
        gateway_url="http://127.0.0.1:8767",
        broker="127.0.0.1",
        port=1883,
        # HTTP waits for Gateway RGB/depth capture. MQTT waits for YOLO result.
        http_timeout_s=15,
        timeout_s=180,
        # Keep captures for debugging. Each request gets its own subdirectory.
        capture_dir="captures",
        # Do not print the full internal client JSON twice; this demo prints a
        # smaller summary below.
        verbose=False,
        # Demo scripts should show the error payload instead of printing a long
        # traceback. Real business scripts can keep the default True when they
        # prefer exceptions.
        raise_on_error=False,
    )

    if result.get("status") != "success":
        print("YOLO Detect MQTT result: error")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    detection = result.get("detection", {})
    offset = result.get("offset", {})
    slope = result.get("slope", {})
    depth = result.get("depth", {})
    server = result.get("server", {})

    print("YOLO Detect MQTT result: success")
    print(f"request_id: {result.get('request_id')}")
    print(f"point1: {detection.get('point1')}")
    print(f"point2: {detection.get('point2')}")
    print(f"line_center: {offset.get('line_center')}")
    print(f"horizontal_offset_px: {offset.get('horizontal_offset_px')}")
    print(f"direction: {offset.get('direction')}")
    print(f"angle_deg: {slope.get('angle_deg')}")
    print(f"center_depth_mm: {depth.get('center_mm')}")
    print(f"server_latency_ms: {server.get('latency_ms')}")
    print(f"server_work_dir: {server.get('work_dir')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
