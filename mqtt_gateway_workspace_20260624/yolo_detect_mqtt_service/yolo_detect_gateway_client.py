#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gateway HTTP capture client for the YOLO Detect MQTT service.

This client is the live-capture path that customer scripts should call when
they do not want to import GDK themselves:

1. Read RGB JPG from the Gateway HTTP snapshot endpoint.
2. Read raw uint16 depth from the Gateway HTTP raw depth endpoint.
3. Save both files locally for debugging.
4. Publish one MQTT detect request.
5. Wait for the matching result on /yolo_detect_result.

The only robot-facing dependency here is HTTP. GDK stays inside the Gateway
service boundary.
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
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from uuid import uuid4

from yolo_detect_client import DEFAULT_REQUEST_TOPIC, DEFAULT_RESULT_TOPIC, make_client


def fetch_bytes(url: str, timeout_s: float) -> tuple[bytes, dict[str, str]]:
    request = Request(url, headers={"User-Agent": "wxf-yolo-detect-gateway-client/1.0"})
    with urlopen(request, timeout=timeout_s) as response:  # noqa: S310 - operator-configured robot LAN URL
        data = response.read()
        headers = {key.lower(): value for key, value in response.headers.items()}
        return data, headers


def header_int(headers: dict[str, str], key: str, default: int) -> int:
    try:
        return int(headers.get(key.lower(), ""))
    except ValueError:
        return default


class GatewayYoloDetectClient:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.request_id = args.request_id or f"detect-gateway-{int(time.time() * 1000)}-{uuid4().hex[:8]}"
        self.done = threading.Event()
        self.result: dict[str, Any] | None = None
        self.client = make_client(args.client_id or f"wxf-yolo-detect-gateway-client-{socket.gethostname()}-{os.getpid()}")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def gateway_url(self, endpoint: str) -> str:
        base = self.args.gateway_url.rstrip("/") + "/"
        return urljoin(base, endpoint.lstrip("/"))

    def capture(self) -> tuple[bytes, bytes, tuple[int, int], Path]:
        capture_dir = Path(self.args.capture_dir)
        capture_dir.mkdir(parents=True, exist_ok=True)
        rgb_url = self.gateway_url(self.args.rgb_endpoint)
        depth_url = self.gateway_url(self.args.depth_raw_endpoint)

        rgb_bytes, rgb_headers = fetch_bytes(rgb_url, self.args.http_timeout_s)
        depth_bytes, depth_headers = fetch_bytes(depth_url, self.args.http_timeout_s)
        depth_height = header_int(depth_headers, "x-g2-depth-height", int(self.args.depth_shape[0]))
        depth_width = header_int(depth_headers, "x-g2-depth-width", int(self.args.depth_shape[1]))
        dtype = depth_headers.get("x-g2-depth-dtype", "uint16")
        if dtype != "uint16":
            raise RuntimeError(f"raw depth dtype must be uint16, got {dtype!r}")
        expected_bytes = depth_height * depth_width * 2
        if len(depth_bytes) != expected_bytes:
            raise RuntimeError(
                f"raw depth size mismatch: got {len(depth_bytes)} bytes, "
                f"expected {expected_bytes} for {depth_height}x{depth_width} uint16"
            )

        stamp = time.strftime("%Y%m%d_%H%M%S")
        run_dir = capture_dir / f"{stamp}_{self.request_id}"
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "head.jpg").write_bytes(rgb_bytes)
        (run_dir / "head_depth.raw").write_bytes(depth_bytes)
        (run_dir / "capture_meta.json").write_text(
            json.dumps(
                {
                    "request_id": self.request_id,
                    "gateway_url": self.args.gateway_url,
                    "rgb_url": rgb_url,
                    "depth_url": depth_url,
                    "rgb_bytes": len(rgb_bytes),
                    "depth_bytes": len(depth_bytes),
                    "depth_shape": [depth_height, depth_width],
                    "depth_dtype": dtype,
                    "rgb_content_type": rgb_headers.get("content-type", ""),
                    "depth_content_type": depth_headers.get("content-type", ""),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return rgb_bytes, depth_bytes, (depth_height, depth_width), run_dir

    def on_connect(self, client: Any, userdata: Any, flags: Any, reason: Any, *extra: Any) -> None:
        reason_value = getattr(reason, "value", reason)
        if reason_value not in (0, "0"):
            self.result = {"status": "error", "request_id": self.request_id, "error": f"MQTT connect failed: {reason}"}
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
        rgb_bytes, depth_bytes, depth_shape, run_dir = self.capture()
        payload = {
            "cmd": "detect",
            "request_id": self.request_id,
            "model_path": self.args.model_path,
            "image": base64.b64encode(rgb_bytes).decode("ascii"),
            "depthimg": base64.b64encode(depth_bytes).decode("ascii"),
            "depth_shape": [int(depth_shape[0]), int(depth_shape[1])],
            "depth_offset_px": int(self.args.depth_offset_px),
            "source": {
                "type": "gateway_http",
                "gateway_url": self.args.gateway_url,
                "capture_dir": str(run_dir),
            },
        }
        self.client.publish(self.args.request_topic, json.dumps(payload, ensure_ascii=False), qos=self.args.qos, retain=False)
        if getattr(self.args, "verbose", True):
            print(
                f"[gateway-client] published {self.args.request_topic} request_id={self.request_id} "
                f"image_bytes={len(rgb_bytes)} depth_bytes={len(depth_bytes)} depth_shape={depth_shape[0]}x{depth_shape[1]}",
                flush=True,
            )

    def run(self) -> int:
        self.client.connect(self.args.broker, self.args.port, keepalive=60)
        self.client.loop_start()
        try:
            if not self.done.wait(timeout=self.args.timeout_s):
                print(f"[gateway-client] timeout waiting for {self.args.result_topic} request_id={self.request_id}", file=sys.stderr)
                return 2
            assert self.result is not None
            text = json.dumps(self.result, ensure_ascii=False, indent=2, sort_keys=True)
            if getattr(self.args, "verbose", True):
                print(text)
            if self.args.output_json:
                Path(self.args.output_json).write_text(text + "\n", encoding="utf-8")
            return 0 if self.result.get("status") == "success" else 1
        finally:
            self.client.loop_stop()
            self.client.disconnect()


def detect_once(
    *,
    gateway_url: str | None = None,
    broker: str | None = None,
    port: int | None = None,
    timeout_s: float = 180.0,
    http_timeout_s: float = 15.0,
    capture_dir: str = "captures",
    model_path: str = "shelf.pt",
    output_json: str = "",
    request_id: str = "",
    raise_on_error: bool = True,
    verbose: bool = False,
) -> dict[str, Any]:
    """Capture RGB/depth through Gateway, run YOLO over MQTT, and return result.

    This is the function customer scripts should import. It deliberately does
    not import GDK. The call path is:

        customer script -> Gateway HTTP -> MQTT YOLO service -> result JSON

    Args:
        gateway_url: Gateway HTTP base URL. Defaults to YOLO_DETECT_GATEWAY_URL
            or http://127.0.0.1:8767.
        broker: MQTT broker host. Defaults to YOLO_DETECT_BROKER or 127.0.0.1.
        port: MQTT broker port. Defaults to YOLO_DETECT_PORT or 1883.
        timeout_s: Total MQTT result wait timeout.
        http_timeout_s: Timeout for each Gateway HTTP capture request.
        capture_dir: Local directory where captured head.jpg/head_depth.raw are saved.
        model_path: Informational model path sent in the MQTT request.
        output_json: Optional path to write the final result JSON.
        request_id: Optional caller-supplied request id for log correlation.
        raise_on_error: Raise RuntimeError when MQTT result status is not success.
        verbose: Print the same progress/result text as the CLI.

    Returns:
        The parsed `/yolo_detect_result` JSON payload.
    """

    args = parse_args([])
    if gateway_url is not None:
        args.gateway_url = gateway_url
    if broker is not None:
        args.broker = broker
    if port is not None:
        args.port = int(port)
    args.timeout_s = float(timeout_s)
    args.http_timeout_s = float(http_timeout_s)
    args.capture_dir = capture_dir
    args.model_path = model_path
    args.output_json = output_json
    args.request_id = request_id
    args.verbose = verbose

    client = GatewayYoloDetectClient(args)
    code = client.run()
    if client.result is None:
        raise TimeoutError(f"timeout waiting for {args.result_topic} request_id={client.request_id}")
    if raise_on_error and code != 0:
        error = client.result.get("error") or client.result
        raise RuntimeError(f"YOLO detect failed: {error}")
    return client.result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gateway-url", default=os.environ.get("YOLO_DETECT_GATEWAY_URL", "http://127.0.0.1:8767"))
    parser.add_argument("--rgb-endpoint", default=os.environ.get("YOLO_DETECT_RGB_ENDPOINT", "/api/cameras/head_rgb/snapshot.jpg"))
    parser.add_argument("--depth-raw-endpoint", default=os.environ.get("YOLO_DETECT_DEPTH_RAW_ENDPOINT", "/api/cameras/head_depth/raw"))
    parser.add_argument("--http-timeout-s", type=float, default=float(os.environ.get("YOLO_DETECT_HTTP_TIMEOUT_S", "10")))
    parser.add_argument("--capture-dir", default=os.environ.get("YOLO_DETECT_CAPTURE_DIR", "captures"))
    parser.add_argument("--broker", default=os.environ.get("YOLO_DETECT_BROKER", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("YOLO_DETECT_PORT", "1883")))
    parser.add_argument("--request-topic", default=os.environ.get("YOLO_DETECT_REQUEST_TOPIC", DEFAULT_REQUEST_TOPIC))
    parser.add_argument("--result-topic", default=os.environ.get("YOLO_DETECT_RESULT_TOPIC", DEFAULT_RESULT_TOPIC))
    parser.add_argument("--client-id", default="")
    parser.add_argument("--qos", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--model-path", default=os.environ.get("YOLO_DETECT_MODEL", "shelf.pt"))
    parser.add_argument("--depth-shape", nargs=2, type=int, default=(400, 640), metavar=("HEIGHT", "WIDTH"))
    parser.add_argument("--depth-offset-px", type=int, default=1)
    parser.add_argument("--request-id", default="")
    parser.add_argument("--timeout-s", type=float, default=180.0)
    parser.add_argument("--output-json", default="last_yolo_detect_gateway_result.json")
    parser.set_defaults(verbose=True)
    parser.add_argument("--quiet", dest="verbose", action="store_false", help="Do not print progress or result JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return GatewayYoloDetectClient(parse_args(argv)).run()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
