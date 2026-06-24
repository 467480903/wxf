#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MQTT YOLO detect server.

Request topic payload:
    {"cmd": "detect", "image": "<base64 jpg>", "depthimg": "<base64 uint16 raw>"}

Result topic payload:
    {"status": "success", "request_id": "...", ... detection result ...}

This process is deliberately a vision-only boundary:

- It subscribes to a detect topic and publishes a result topic.
- It does not import GDK, initialize robot SDKs, or send motion commands.
- The model is loaded once at process startup, so each request only pays image
  decode + inference + result publish time.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import sys
import time
import traceback
from pathlib import Path
from typing import Any
from uuid import uuid4

from yolo_detect_core import DetectionError, YoloDepthDetector


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


def decode_b64(value: Any, field: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty base64 string")
    text = value.strip()
    if "," in text and text.lower().startswith("data:"):
        text = text.split(",", 1)[1]
    try:
        return base64.b64decode(text, validate=True)
    except Exception as exc:
        raise ValueError(f"{field} base64 decode failed: {type(exc).__name__}: {exc}") from exc


def safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)[:80] or uuid4().hex


def parse_shape(value: Any, default: tuple[int, int]) -> tuple[int, int]:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return int(value[0]), int(value[1])
    return default


class YoloDetectMqttServer:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.host = socket.gethostname()
        self.client = make_client(args.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.work_dir = Path(args.work_dir).resolve()
        self.requests_dir = self.work_dir / "requests"
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.depth_shape = (int(args.depth_shape[0]), int(args.depth_shape[1]))
        if args.device == "cpu":
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
        print(f"[server] loading model={args.model} device={args.device}", flush=True)
        self.detector = YoloDepthDetector(args.model, device=args.device)
        print("[server] model loaded", flush=True)

    def on_connect(self, client: Any, userdata: Any, flags: Any, reason: Any, *extra: Any) -> None:
        reason_value = getattr(reason, "value", reason)
        if reason_value not in (0, "0"):
            print(f"[mqtt] connect failed: {reason}", flush=True)
            return
        print(f"[mqtt] connected broker={self.args.broker}:{self.args.port}", flush=True)
        client.subscribe(self.args.request_topic, qos=self.args.qos)
        print(f"[mqtt] subscribed {self.args.request_topic}", flush=True)

    def on_message(self, client: Any, userdata: Any, message: Any) -> None:
        started = time.monotonic()
        request_id = f"detect-{int(time.time() * 1000)}-{uuid4().hex[:8]}"
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("MQTT payload must be a JSON object")
            request_id = safe_id(str(payload.get("request_id") or request_id))
            result = self.handle_request(payload, request_id, started)
        except Exception as exc:  # noqa: BLE001 - MQTT boundary must publish errors as data
            result = self.error_payload(request_id, exc, started)
        self.publish_result(result)

    def handle_request(self, payload: dict[str, Any], request_id: str, started: float) -> dict[str, Any]:
        if payload.get("cmd") != "detect":
            raise ValueError(f"unsupported cmd: {payload.get('cmd')!r}")
        request_dir = self.requests_dir / f"{time.strftime('%Y%m%d_%H%M%S')}_{request_id}"
        request_dir.mkdir(parents=True, exist_ok=False)

        # The customer protocol sends both images inside one MQTT JSON message.
        # image is an RGB/JPEG frame. depthimg is the raw uint16 depth buffer,
        # not the colored depth JPG. Keeping the raw depth is what lets the
        # detector return millimeter values in the result.
        image_bytes = decode_b64(payload.get("image"), "image")
        depth_bytes = decode_b64(payload.get("depthimg"), "depthimg")
        image_path = request_dir / "head.jpg"
        depth_path = request_dir / "head_depth.raw"
        image_path.write_bytes(image_bytes)
        depth_path.write_bytes(depth_bytes)
        meta = {
            "request_id": request_id,
            "received_at": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "image_bytes": len(image_bytes),
            "depth_bytes": len(depth_bytes),
            "payload_keys": sorted(payload.keys()),
        }
        (request_dir / "request_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        depth_shape = parse_shape(payload.get("depth_shape"), self.depth_shape)
        depth_offset_px = int(payload.get("depth_offset_px", self.args.depth_offset_px))
        result = self.detector.detect(
            image_path=image_path,
            depth_raw_path=depth_path,
            output_dir=request_dir,
            depth_shape=depth_shape,
            depth_offset_px=depth_offset_px,
            conf=self.args.conf,
            imgsz=self.args.imgsz,
        )
        result.update(
            {
                "status": "success",
                "cmd": "detect",
                "request_id": request_id,
                "server": {
                    "hostname": self.host,
                    "device": self.args.device,
                    "broker": f"{self.args.broker}:{self.args.port}",
                    "work_dir": str(request_dir),
                    "latency_ms": round((time.monotonic() - started) * 1000.0, 2),
                },
            }
        )
        (request_dir / "mqtt_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[detect] success request_id={request_id} latency_ms={result['server']['latency_ms']}", flush=True)
        return result

    def error_payload(self, request_id: str, exc: Exception, started: float) -> dict[str, Any]:
        error = f"{type(exc).__name__}: {exc}"
        print(f"[detect] error request_id={request_id}: {error}", flush=True)
        if self.args.traceback_on_error:
            traceback.print_exc()
        return {
            "status": "error",
            "cmd": "detect",
            "request_id": request_id,
            "error": error,
            "server": {
                "hostname": self.host,
                "device": self.args.device,
                "latency_ms": round((time.monotonic() - started) * 1000.0, 2),
            },
        }

    def publish_result(self, result: dict[str, Any]) -> None:
        payload = json.dumps(result, ensure_ascii=False, sort_keys=True)
        self.client.publish(self.args.result_topic, payload, qos=self.args.qos, retain=False)
        print(f"[mqtt] published {self.args.result_topic} request_id={result.get('request_id')} status={result.get('status')}", flush=True)

    def run(self) -> None:
        self.client.connect(self.args.broker, self.args.port, keepalive=60)
        try:
            self.client.loop_forever()
        except KeyboardInterrupt:
            print("[server] stopped", flush=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", default=os.environ.get("YOLO_DETECT_BROKER", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("YOLO_DETECT_PORT", "1883")))
    parser.add_argument("--request-topic", default=os.environ.get("YOLO_DETECT_REQUEST_TOPIC", DEFAULT_REQUEST_TOPIC))
    parser.add_argument("--result-topic", default=os.environ.get("YOLO_DETECT_RESULT_TOPIC", DEFAULT_RESULT_TOPIC))
    parser.add_argument("--client-id", default=f"wxf-yolo-detect-server-{socket.gethostname()}-{os.getpid()}")
    parser.add_argument("--qos", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--model", default=os.environ.get("YOLO_DETECT_MODEL", "shelf.pt"))
    parser.add_argument("--device", default=os.environ.get("YOLO_DETECT_DEVICE", "cpu"))
    parser.add_argument("--work-dir", default=os.environ.get("YOLO_DETECT_WORK_DIR", "runs"))
    parser.add_argument("--depth-shape", nargs=2, type=int, default=(400, 640), metavar=("HEIGHT", "WIDTH"))
    parser.add_argument("--depth-offset-px", type=int, default=1)
    parser.add_argument("--conf", type=float, default=None)
    parser.add_argument("--imgsz", type=int, default=None)
    parser.add_argument("--traceback-on-error", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.device == "cpu":
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
    server = YoloDetectMqttServer(args)
    server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
