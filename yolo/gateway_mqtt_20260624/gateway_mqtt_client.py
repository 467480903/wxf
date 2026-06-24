#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-shot client for the G2 gateway MQTT task interface.

This file is intentionally self-contained so the migrated yolo scripts can run
from this directory without importing the robot SDK or the gateway source tree.
It publishes one ``g2.task.v1`` request, waits for the matching terminal result,
prints JSON, and exits.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from typing import Any
from uuid import uuid4


SCHEMA = "g2.task.v1"
TERMINAL_STATES = {"DONE", "FAILED", "BLOCKED", "CANCELED"}
PREFLIGHT_POLICIES = {"require", "warn", "skip"}


def _mqtt_connect_ok(reason: Any) -> bool:
    if reason in (0, "0"):
        return True
    if str(reason).lower() in {"success", "normal disconnection"}:
        return True
    value = getattr(reason, "value", None)
    return value == 0


def make_task_id(prefix: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in prefix)[:36] or "yolo"
    return f"{safe}-{os.getpid()}-{int(time.time() * 1000)}-{uuid4().hex[:8]}"


def _make_paho_client(client_id: str) -> Any:
    try:
        import paho.mqtt.client as mqtt
    except Exception as exc:  # noqa: BLE001 - dependency boundary
        raise RuntimeError("paho-mqtt is required for gateway MQTT scripts") from exc

    callback_api = getattr(mqtt, "CallbackAPIVersion", None)
    if callback_api is not None:
        try:
            return mqtt.Client(callback_api_version=callback_api.VERSION2, client_id=client_id)
        except TypeError:
            pass
    return mqtt.Client(client_id=client_id)


class GatewayMqttClient:
    def __init__(
        self,
        broker: str = "127.0.0.1",
        port: int = 1883,
        client_id: str | None = None,
        qos: int = 1,
        keepalive_s: int = 30,
    ) -> None:
        self.broker = broker
        self.port = port
        self.qos = qos
        self.keepalive_s = keepalive_s
        self.client_id = client_id or make_task_id("yolo-gateway-client")

        self.request_topic = "g2/gateway/task/request"
        self.status_topic = "g2/gateway/task/status"
        self.result_topic = "g2/gateway/task/result"
        self.ready_topic = "g2/gateway/state/ready"
        self.capabilities_topic = "g2/gateway/capabilities"
        self.fault_topic = "g2/gateway/event/fault"

        self.client = _make_paho_client(self.client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        self.connected_event = threading.Event()
        self.ready_event = threading.Event()
        self.capabilities_event = threading.Event()
        self.result_event = threading.Event()

        self.task_id = ""
        self.ready_payload: dict[str, Any] | None = None
        self.capabilities_payload: dict[str, Any] | None = None
        self.result: dict[str, Any] | None = None
        self.messages: list[tuple[str, dict[str, Any]]] = []
        self.preflight_warnings: list[str] = []

    def submit_and_wait(
        self,
        payload: dict[str, Any],
        timeout_s: float = 15.0,
        preflight: str = "require",
        preflight_timeout_s: float = 3.0,
    ) -> dict[str, Any]:
        self.task_id = str(payload.get("task_id") or "")
        if not self.task_id:
            raise ValueError("payload requires task_id")
        if preflight not in PREFLIGHT_POLICIES:
            raise ValueError(f"preflight must be one of: {sorted(PREFLIGHT_POLICIES)}")

        self.client.connect(self.broker, self.port, self.keepalive_s)
        self.client.loop_start()
        try:
            if not self.connected_event.wait(timeout=min(timeout_s, 5.0)):
                raise TimeoutError("MQTT connect timed out")
            self._run_preflight(payload, preflight, min(timeout_s, preflight_timeout_s))
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            self.client.publish(self.request_topic, body, qos=self.qos)
            if not self.result_event.wait(timeout=timeout_s):
                raise TimeoutError(f"timed out waiting for MQTT result for {self.task_id}")
            assert self.result is not None
            if self.preflight_warnings:
                self.result = {**self.result, "preflight_warnings": list(self.preflight_warnings)}
            return self.result
        finally:
            self.client.loop_stop()
            self.client.disconnect()

    def _on_connect(self, client: Any, userdata: Any, flags: Any, reason: Any, *extra: Any) -> None:
        if not _mqtt_connect_ok(reason):
            self.result = {"task_id": self.task_id, "state": "FAILED", "error": f"MQTT connect failed: {reason}"}
            self.result_event.set()
            return
        for topic in (
            self.status_topic,
            self.result_topic,
            self.ready_topic,
            self.capabilities_topic,
            self.fault_topic,
        ):
            client.subscribe(topic, qos=self.qos)
        self.connected_event.set()

    def _on_message(self, client: Any, userdata: Any, message: Any) -> None:
        topic = str(getattr(message, "topic", ""))
        raw = getattr(message, "payload", b"{}")
        try:
            payload = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else str(raw))
            if not isinstance(payload, dict):
                raise ValueError("MQTT payload must be a JSON object")
        except Exception as exc:  # noqa: BLE001 - MQTT boundary
            payload = {"event": "payload_decode_error", "error": f"{type(exc).__name__}: {exc}"}

        self.messages.append((topic, payload))
        if topic == self.ready_topic:
            self.ready_payload = payload
            self.ready_event.set()
            return
        if topic == self.capabilities_topic:
            self.capabilities_payload = payload
            self.capabilities_event.set()
            return
        if topic == self.fault_topic and payload.get("task_id") in {None, self.task_id}:
            self.result = {"task_id": self.task_id, "state": "FAILED", "error": payload}
            self.result_event.set()
            return
        if topic == self.result_topic and payload.get("task_id") == self.task_id:
            self.result = payload
            self.result_event.set()
            return
        if topic == self.status_topic and payload.get("task_id") == self.task_id:
            if payload.get("state") in TERMINAL_STATES:
                self.result = payload
                self.result_event.set()

    def _run_preflight(self, payload: dict[str, Any], preflight: str, timeout_s: float) -> None:
        if preflight == "skip":
            return
        try:
            self._require_ready(timeout_s)
            self._require_capability(payload, timeout_s)
        except Exception as exc:
            if preflight == "warn":
                self.preflight_warnings.append(f"{type(exc).__name__}: {exc}")
                return
            raise

    def _require_ready(self, timeout_s: float) -> None:
        if not self.ready_event.wait(timeout=max(0.0, timeout_s)):
            raise TimeoutError(f"timed out waiting for retained ready topic: {self.ready_topic}")
        assert self.ready_payload is not None
        if not self.ready_payload.get("ok"):
            raise RuntimeError(f"gateway not ready: {self.ready_payload}")

    def _require_capability(self, payload: dict[str, Any], timeout_s: float) -> None:
        if not self.capabilities_event.wait(timeout=max(0.0, timeout_s)):
            raise TimeoutError(f"timed out waiting for retained capabilities topic: {self.capabilities_topic}")
        assert self.capabilities_payload is not None
        capabilities = self.capabilities_payload.get("capabilities", [])
        if not isinstance(capabilities, list):
            raise RuntimeError(f"invalid capabilities payload: {self.capabilities_payload}")

        command = str(payload.get("command") or "")
        mode = str(payload.get("mode") or "")
        capability = next(
            (item for item in capabilities if isinstance(item, dict) and item.get("name") == command),
            None,
        )
        if capability is None:
            raise ValueError(f"capability not advertised by gateway: {command}")
        if capability.get("enabled") is False:
            raise ValueError(f"capability disabled by gateway: {command}")
        modes = capability.get("modes", [])
        if isinstance(modes, list) and modes and mode not in modes:
            raise ValueError(f"mode {mode!r} not advertised for {command}; allowed={modes}")


def build_payload(
    command: str,
    args: dict[str, Any] | None = None,
    mode: str = "dry_run",
    task_id: str | None = None,
    confirm_physical: bool = False,
    submitted_by: str = "yolo-gateway-mqtt",
    timeout_s: float | None = None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "task_id": task_id or make_task_id(command),
        "command": command,
        "mode": mode,
        "args": args or {},
        "timeout_s": timeout_s,
        "confirm_physical": bool(confirm_physical),
        "submitted_by": submitted_by,
    }


def run_gateway_task(
    command: str,
    args: dict[str, Any] | None = None,
    mode: str = "dry_run",
    timeout_s: float = 15.0,
    preflight: str = "require",
    preflight_timeout_s: float = 3.0,
    broker: str | None = None,
    port: int | None = None,
    task_id: str | None = None,
    submitted_by: str = "yolo-gateway-mqtt",
) -> dict[str, Any]:
    payload = build_payload(
        command=command,
        args=args,
        mode=mode,
        task_id=task_id,
        submitted_by=submitted_by,
        timeout_s=timeout_s,
    )
    client = GatewayMqttClient(
        broker=broker or os.environ.get("G2_GATEWAY_MQTT_BROKER", "127.0.0.1"),
        port=port or int(os.environ.get("G2_GATEWAY_MQTT_PORT", "1883")),
    )
    return client.submit_and_wait(
        payload,
        timeout_s=timeout_s,
        preflight=preflight,
        preflight_timeout_s=preflight_timeout_s,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", default=os.environ.get("G2_GATEWAY_MQTT_BROKER", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("G2_GATEWAY_MQTT_PORT", "1883")))
    parser.add_argument("--command", default="gdk.read_power_state")
    parser.add_argument("--mode", default="read_only")
    parser.add_argument("--args-json", default="{}")
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--timeout-s", type=float, default=15.0)
    parser.add_argument("--preflight", choices=sorted(PREFLIGHT_POLICIES), default="require")
    parser.add_argument("--preflight-timeout-s", type=float, default=3.0)
    parser.add_argument("--submitted-by", default="yolo-gateway-mqtt")
    parser.add_argument("--show-messages", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload_args = json.loads(args.args_json)
        if not isinstance(payload_args, dict):
            raise ValueError("--args-json must decode to a JSON object")
        client = GatewayMqttClient(broker=args.broker, port=args.port)
        result = client.submit_and_wait(
            build_payload(
                command=args.command,
                args=payload_args,
                mode=args.mode,
                task_id=args.task_id,
                submitted_by=args.submitted_by,
                timeout_s=args.timeout_s,
            ),
            timeout_s=args.timeout_s,
            preflight=args.preflight,
            preflight_timeout_s=args.preflight_timeout_s,
        )
        if args.show_messages:
            for topic, payload in client.messages:
                print(json.dumps({"topic": topic, "payload": payload}, ensure_ascii=False, sort_keys=True))
    except Exception as exc:  # noqa: BLE001 - CLI returns a machine-readable failure
        result = {"task_id": args.task_id, "state": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
    return 0 if result.get("state") == "DONE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
