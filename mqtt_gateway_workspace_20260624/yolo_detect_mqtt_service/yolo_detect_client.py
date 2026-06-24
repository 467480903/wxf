#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""File-based MQTT client for the YOLO detect service.

This first client is intentionally file-based. It reads an existing RGB image
and an existing depth raw file, converts both to base64, sends one MQTT detect
request, and waits for the matching result_id on the result topic.

It does not import GDK and does not capture from the camera directly. For live
capture without GDK in the customer script, add a read-only Gateway endpoint for
raw depth later, then replace the file reads here with HTTP reads.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any
from uuid import uuid4


DEFAULT_REQUEST_TOPIC = "/yolo_detect/"
DEFAULT_RESULT_TOPIC = "/yolo_detect_result"


def make_client(client_id: str) -> Any:
    import paho.mqtt.client as mqtt

    callback_api = getattr(mqtt, "CallbackAPIVersion", None)
    if callback_api is not None:
        try:
            return mqtt.Client(callback_api_version=callback_api.VERSION2, client_id=client_id)
        except TypeError:
            pass
    return mqtt.Client(client_id=client_id)


class YoloDetectClient:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.request_id = args.request_id or f"detect-client-{int(time.time() * 1000)}-{uuid4().hex[:8]}"
        self.done = threading.Event()
        self.result: dict[str, Any] | None = None
        self.client = make_client(args.client_id or f"wxf-yolo-detect-client-{socket.gethostname()}-{os.getpid()}")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client: Any, userdata: Any, flags: Any, reason: Any, *extra: Any) -> None:
        reason_value = getattr(reason, "value", reason)
        if reason_value not in (0, "0"):
            self.result = {"status": "error", "error": f"MQTT connect failed: {reason}"}
            self.done.set()
            return
        client.subscribe(self.args.result_topic, qos=self.args.qos)
        self.publish_request()

    def on_message(self, client: Any, userdata: Any, message: Any) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except Exception as exc:
            payload = {"status": "error", "error": f"result decode failed: {type(exc).__name__}: {exc}"}
        if not isinstance(payload, dict):
            payload = {"status": "error", "error": "result payload is not a JSON object"}
        if payload.get("request_id") != self.request_id:
            return
        self.result = payload
        self.done.set()

    def publish_request(self) -> None:
        rgb_path = Path(self.args.rgb_path)
        depth_path = Path(self.args.depth_raw_path)
        image_b64 = base64.b64encode(rgb_path.read_bytes()).decode("ascii")
        depth_b64 = base64.b64encode(depth_path.read_bytes()).decode("ascii")
        payload = {
            "cmd": "detect",
            "request_id": self.request_id,
            "model_path": self.args.model_path,
            "image": image_b64,
            "depthimg": depth_b64,
            "depth_shape": [int(self.args.depth_shape[0]), int(self.args.depth_shape[1])],
            "depth_offset_px": int(self.args.depth_offset_px),
        }
        self.client.publish(self.args.request_topic, json.dumps(payload, ensure_ascii=False), qos=self.args.qos, retain=False)
        print(
            f"[client] published {self.args.request_topic} request_id={self.request_id} "
            f"image_bytes={rgb_path.stat().st_size} depth_bytes={depth_path.stat().st_size}",
            flush=True,
        )

    def run(self) -> int:
        self.client.connect(self.args.broker, self.args.port, keepalive=60)
        self.client.loop_start()
        try:
            if not self.done.wait(timeout=self.args.timeout_s):
                print(f"[client] timeout waiting for {self.args.result_topic} request_id={self.request_id}", file=sys.stderr)
                return 2
            assert self.result is not None
            text = json.dumps(self.result, ensure_ascii=False, indent=2, sort_keys=True)
            print(text)
            if self.args.output_json:
                Path(self.args.output_json).write_text(text + "\n", encoding="utf-8")
            return 0 if self.result.get("status") == "success" else 1
        finally:
            self.client.loop_stop()
            self.client.disconnect()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", default=os.environ.get("YOLO_DETECT_BROKER", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("YOLO_DETECT_PORT", "1883")))
    parser.add_argument("--request-topic", default=os.environ.get("YOLO_DETECT_REQUEST_TOPIC", DEFAULT_REQUEST_TOPIC))
    parser.add_argument("--result-topic", default=os.environ.get("YOLO_DETECT_RESULT_TOPIC", DEFAULT_RESULT_TOPIC))
    parser.add_argument("--client-id", default="")
    parser.add_argument("--qos", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--rgb-path", default="head.jpg")
    parser.add_argument("--depth-raw-path", default="head_depth.raw")
    parser.add_argument("--model-path", default="shelf.pt")
    parser.add_argument("--depth-shape", nargs=2, type=int, default=(400, 640), metavar=("HEIGHT", "WIDTH"))
    parser.add_argument("--depth-offset-px", type=int, default=1)
    parser.add_argument("--request-id", default="")
    parser.add_argument("--timeout-s", type=float, default=60.0)
    parser.add_argument("--output-json", default="last_yolo_detect_result.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return YoloDetectClient(parse_args(argv)).run()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
