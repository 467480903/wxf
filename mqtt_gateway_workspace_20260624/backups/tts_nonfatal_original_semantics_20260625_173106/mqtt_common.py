#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4


SCHEMA = "g2.task.v1"
TERMINAL_STATES = {"DONE", "FAILED", "BLOCKED", "CANCELED"}
PREFLIGHT_POLICIES = {"require", "warn", "skip"}
ORIGINAL_ROOT = Path("/data/wxf/wxf")
DEFAULT_HTTP_URL = os.environ.get("G2_GATEWAY_HTTP_URL", "http://127.0.0.1:8767").rstrip("/")
SEQUENCE_DEADLINE_ENV = "G2_WXF_SEQUENCE_DEADLINE_TS"


def workspace_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "mqtt_common").is_dir() and (parent / "positions").exists():
            return parent
    return current.parents[1]


ROOT = workspace_root()


def _mqtt_connect_ok(reason: Any) -> bool:
    if reason in (0, "0"):
        return True
    if str(reason).lower() in {"success", "normal disconnection"}:
        return True
    return getattr(reason, "value", None) == 0


def make_task_id(prefix: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in prefix)[:42] or "wxf"
    return f"{safe}-{os.getpid()}-{int(time.time() * 1000)}-{uuid4().hex[:8]}"


def _make_client(client_id: str) -> Any:
    try:
        import paho.mqtt.client as mqtt
    except Exception as exc:
        raise RuntimeError("paho-mqtt is required for MQTT/Gateway scripts") from exc
    callback_api = getattr(mqtt, "CallbackAPIVersion", None)
    if callback_api is not None:
        try:
            return mqtt.Client(callback_api_version=callback_api.VERSION2, client_id=client_id)
        except TypeError:
            pass
    return mqtt.Client(client_id=client_id)


class GatewayMqttClient:
    def __init__(self, broker: str = "127.0.0.1", port: int = 1883, qos: int = 1) -> None:
        self.broker = broker
        self.port = port
        self.qos = qos
        self.client_id = make_task_id("wxf-gateway-client")
        self.request_topic = "g2/gateway/task/request"
        self.status_topic = "g2/gateway/task/status"
        self.result_topic = "g2/gateway/task/result"
        self.ready_topic = "g2/gateway/state/ready"
        self.capabilities_topic = "g2/gateway/capabilities"
        self.fault_topic = "g2/gateway/event/fault"
        self.client = _make_client(self.client_id)
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
        self.client.connect(self.broker, self.port, 30)
        self.client.loop_start()
        try:
            if not self.connected_event.wait(timeout=min(timeout_s, 5.0)):
                raise TimeoutError("MQTT connect timed out")
            self._run_preflight(payload, preflight, min(timeout_s, preflight_timeout_s))
            self.client.publish(self.request_topic, json.dumps(payload, ensure_ascii=False, sort_keys=True), qos=self.qos)
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
        for topic in (self.status_topic, self.result_topic, self.ready_topic, self.capabilities_topic, self.fault_topic):
            client.subscribe(topic, qos=self.qos)
        self.connected_event.set()

    def _on_message(self, client: Any, userdata: Any, message: Any) -> None:
        topic = str(getattr(message, "topic", ""))
        raw = getattr(message, "payload", b"{}")
        try:
            payload = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else str(raw))
            if not isinstance(payload, dict):
                raise ValueError("MQTT payload must be a JSON object")
        except Exception as exc:
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
        if topic == self.status_topic and payload.get("task_id") == self.task_id and payload.get("state") in TERMINAL_STATES:
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
        capability = next((item for item in capabilities if isinstance(item, dict) and item.get("name") == command), None)
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
    submitted_by: str = "wxf-mqtt-workspace",
    timeout_s: float | None = None,
    confirm_physical: bool = False,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "task_id": task_id or make_task_id(command),
        "command": command,
        "mode": mode,
        "args": args or {},
        "timeout_s": timeout_s,
        "confirm_physical": bool(confirm_physical),
        "priority": 50,
        "submitted_by": submitted_by,
    }


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw in (None, ""):
        return float(default)
    return float(raw)


def sequence_remaining_s() -> float | None:
    raw = os.environ.get(SEQUENCE_DEADLINE_ENV)
    if raw in (None, ""):
        return None
    try:
        return float(raw) - time.time()
    except ValueError:
        return None


def require_sequence_budget(label: str, min_remaining_s: float = 1.0) -> None:
    remaining = sequence_remaining_s()
    if remaining is not None and remaining < min_remaining_s:
        raise SystemExit(
            f"sequence timeout before {label}: remaining={remaining:.1f}s, "
            f"required>={min_remaining_s:.1f}s"
        )


def effective_task_timeout(timeout_s: float, min_remaining_s: float = 1.0) -> float:
    require_sequence_budget("task submit", min_remaining_s=min_remaining_s)
    remaining = sequence_remaining_s()
    if remaining is None:
        return float(timeout_s)
    return max(min_remaining_s, min(float(timeout_s), remaining))


def nav_timeouts_from_env() -> tuple[float, float]:
    nav_timeout_s = env_float("G2_WXF_NAV_TIMEOUT_S", 120.0)
    client_timeout_s = env_float("G2_WXF_NAV_CLIENT_TIMEOUT_S", 150.0)
    remaining = sequence_remaining_s()
    if remaining is not None:
        if remaining <= 5.0:
            raise SystemExit(f"sequence timeout before nav waypoint: remaining={remaining:.1f}s")
        nav_timeout_s = min(nav_timeout_s, max(5.0, remaining - 5.0))
        client_timeout_s = min(client_timeout_s, nav_timeout_s + 30.0)
        client_timeout_s = max(client_timeout_s, nav_timeout_s + 5.0)
    return nav_timeout_s, client_timeout_s


def safe_motion_mode(mode: str | None = None) -> str:
    selected = (mode or os.environ.get("G2_WXF_GATEWAY_MODE", "dry_run")).strip()
    if selected == "live":
        if not env_flag("G2_WXF_GATEWAY_CONFIRM_PHYSICAL", False):
            raise SystemExit("live mode requires G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1")
        return selected
    if selected not in {"dry_run", "mock"}:
        raise SystemExit(f"Only dry_run/mock/live are allowed in this migrated workspace, got {selected!r}")
    return selected


def submit_task(
    command: str,
    args: dict[str, Any] | None = None,
    mode: str | None = None,
    timeout_s: float = 15.0,
    preflight: str | None = None,
    confirm_physical: bool | None = None,
) -> dict[str, Any]:
    selected_mode = mode or ("read_only" if command.startswith("gdk.read_") or command.endswith(".preflight") else safe_motion_mode())
    selected_confirm = (
        bool(confirm_physical)
        if confirm_physical is not None
        else (selected_mode == "live" and env_flag("G2_WXF_GATEWAY_CONFIRM_PHYSICAL", False))
    )
    effective_timeout_s = effective_task_timeout(timeout_s)
    payload = build_payload(
        command,
        args=args,
        mode=selected_mode,
        timeout_s=effective_timeout_s,
        confirm_physical=selected_confirm,
    )
    client = GatewayMqttClient(
        broker=os.environ.get("G2_GATEWAY_MQTT_BROKER", "127.0.0.1"),
        port=int(os.environ.get("G2_GATEWAY_MQTT_PORT", "1883")),
    )
    result = client.submit_and_wait(
        payload,
        timeout_s=effective_timeout_s,
        preflight=preflight or os.environ.get("G2_WXF_GATEWAY_PREFLIGHT", "require"),
        preflight_timeout_s=env_float("G2_WXF_GATEWAY_PREFLIGHT_TIMEOUT_S", 3.0),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
    return result


def require_done(result: dict[str, Any]) -> None:
    if result.get("state") != "DONE":
        raise SystemExit(1)


def pose_name_from_path(path: str | os.PathLike[str], prefix: str) -> str:
    stem = Path(path).stem or "unnamed"
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in stem)
    return f"{prefix}_{safe}"


def resolve_data_path(raw_path: str | os.PathLike[str]) -> Path:
    raw = Path(raw_path)
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
        try:
            relative = raw.relative_to(ORIGINAL_ROOT)
            candidates.insert(0, ROOT / relative)
        except ValueError:
            candidates.insert(0, ROOT / "positions" / raw.name)
    else:
        cwd = Path.cwd()
        candidates.extend([
            (cwd / raw).resolve(),
            (Path(__file__).resolve().parent / raw).resolve(),
            (ROOT / raw).resolve(),
            (ROOT / "positions" / raw.name).resolve(),
            (ORIGINAL_ROOT / raw).resolve(),
            (ORIGINAL_ROOT / "positions" / raw.name).resolve(),
        ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else raw


def load_json(path: str | os.PathLike[str]) -> dict[str, Any]:
    resolved = resolve_data_path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"JSON file not found: {resolved}")
    with resolved.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {resolved}")
    return data

def resolve_yolo_result_path(preferred: str = "yolo_depth_result.json", base: Path | None = None) -> Path:
    names: list[str] = []
    for name in (preferred, "yyolo_depth_result.json", "yolo_depth_result.json"):
        if name not in names:
            names.append(name)
    candidates: list[Path] = []
    for name in names:
        raw = Path(name)
        if base is not None and not raw.is_absolute():
            candidates.append((base / raw).resolve())
        candidates.append(resolve_data_path(raw))
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    existing = [candidate for candidate in unique if candidate.exists()]
    if not existing:
        return unique[0] if unique else resolve_data_path(preferred)
    return max(existing, key=lambda candidate: candidate.stat().st_mtime)


def load_yolo_result_json(preferred: str = "yolo_depth_result.json", base: Path | None = None) -> tuple[Path, dict[str, Any]]:
    result_path = resolve_yolo_result_path(preferred, base=base)
    with result_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YOLO result JSON root must be an object: {result_path}")
    return result_path, data


def _extract_values(data: dict[str, Any], keys: list[str]) -> list[float]:
    return [float(data.get(key, 0.0)) for key in keys]


def run_arm_json(json_path: str, source_script: str, pose_prefix: str = "arm_json") -> None:
    data = load_json(json_path)
    left = _extract_values(data, LEFT_ARM_KEYS)
    right = _extract_values(data, RIGHT_ARM_KEYS)
    result = submit_task(
        "arm.move_named_pose",
        {
            "pose": pose_name_from_path(json_path, pose_prefix),
            "source_script": source_script,
            "source_json": str(json_path),
            "resolved_json": str(resolve_data_path(json_path)),
            "left_arm_joint_names": LEFT_ARM_KEYS,
            "right_arm_joint_names": RIGHT_ARM_KEYS,
            "left_arm_rad": left,
            "right_arm_rad": right,
            "joint_positions_rad": left + right,
            "joint_velocities_radps": [0.2] * 14,
            "time_scale_s": 2,
        },
        mode=safe_motion_mode(),
        timeout_s=20.0,
    )
    require_done(result)


def run_arm_named_pose(source_script: str, pose: str, joint_positions: list[float] | None = None) -> None:
    args = {"pose": pose, "source_script": source_script}
    if joint_positions is not None:
        args["joint_positions_rad"] = joint_positions
        args["joint_velocities_radps"] = [0.2] * len(joint_positions)
    result = submit_task("arm.move_named_pose", args, mode=safe_motion_mode(), timeout_s=20.0)
    require_done(result)


def run_waist_json(json_path: str, source_script: str, pose_prefix: str = "waist_json") -> None:
    data = load_json(json_path)
    waist = _extract_values(data, WAIST_KEYS)
    result = submit_task(
        "waist.move_named_pose",
        {
            "pose": pose_name_from_path(json_path, pose_prefix),
            "source_script": source_script,
            "source_json": str(json_path),
            "resolved_json": str(resolve_data_path(json_path)),
            "waist_joint_names": WAIST_KEYS,
            "joint_positions_rad": waist,
            "joint_velocities_radps": [0.3] * 5,
        },
        mode=safe_motion_mode(),
        timeout_s=15.0,
    )
    require_done(result)


def run_waist_named_pose(source_script: str, pose: str, joint_positions: list[float] | None = None) -> None:
    args = {"pose": pose, "source_script": source_script}
    if joint_positions is not None:
        args["joint_positions_rad"] = joint_positions
        args["joint_velocities_radps"] = [0.3] * len(joint_positions)
    result = submit_task("waist.move_named_pose", args, mode=safe_motion_mode(), timeout_s=15.0)
    require_done(result)


def run_head_named(source_script: str, yaw_rad: float = 0.0, pitch_rad: float = 0.0, roll_rad: float = 0.0) -> None:
    result = submit_task(
        "head.set_pan_tilt",
        {
            "source_script": source_script,
            "yaw_deg": math.degrees(yaw_rad),
            "pitch_deg": math.degrees(pitch_rad),
            "roll_deg": math.degrees(roll_rad),
        },
        mode=safe_motion_mode(),
        timeout_s=5.0,
    )
    require_done(result)


def run_whole_body_json(json_path: str, source_script: str, sync_requested: bool = False) -> None:
    data = load_json(json_path)
    head = _extract_values(data, HEAD_KEYS)
    waist = _extract_values(data, WAIST_KEYS)
    left = _extract_values(data, LEFT_ARM_KEYS)
    right = _extract_values(data, RIGHT_ARM_KEYS)
    pose = pose_name_from_path(json_path, "whole_body_json")
    if env_flag("G2_WXF_FAST_WHOLE_BODY_SPLIT", False):
        split_delay_s = env_float("G2_WXF_FAST_WHOLE_BODY_SPLIT_DELAY_S", 0.08)
        if not env_flag("G2_WXF_FAST_WHOLE_BODY_SKIP_HEAD", False):
            result = submit_task(
                "head.set_pan_tilt",
                {
                    "source_script": source_script,
                    "source_json": str(json_path),
                    "resolved_json": str(resolve_data_path(json_path)),
                    "yaw_deg": math.degrees(head[0]),
                    "pitch_deg": math.degrees(head[1]),
                    "roll_deg": math.degrees(head[2]),
                    "speed_rad_s": env_float("G2_WXF_FAST_HEAD_SPEED_RADPS", 0.5),
                    "fast_demo_path": True,
                    "whole_body_split": True,
                },
                mode=safe_motion_mode(),
                timeout_s=5.0,
            )
            require_done(result)
            if split_delay_s:
                time.sleep(split_delay_s)

        result = submit_task(
            "waist.move_named_pose",
            {
                "pose": f"{pose}_waist",
                "source_script": source_script,
                "source_json": str(json_path),
                "resolved_json": str(resolve_data_path(json_path)),
                "waist_joint_names": WAIST_KEYS,
                "joint_positions_rad": waist,
                "joint_velocities_radps": [env_float("G2_WXF_FAST_WAIST_SPEED_RADPS", 1.0)] * 5,
                "fast_demo_path": True,
                "whole_body_split": True,
            },
            mode=safe_motion_mode(),
            timeout_s=15.0,
        )
        require_done(result)
        if split_delay_s:
            time.sleep(split_delay_s)

        result = submit_task(
            "arm.move_named_pose",
            {
                "pose": f"{pose}_arms",
                "source_script": source_script,
                "source_json": str(json_path),
                "resolved_json": str(resolve_data_path(json_path)),
                "left_arm_joint_names": LEFT_ARM_KEYS,
                "right_arm_joint_names": RIGHT_ARM_KEYS,
                "left_arm_rad": left,
                "right_arm_rad": right,
                "joint_positions_rad": left + right,
                "joint_velocities_radps": [env_float("G2_WXF_FAST_ARM_SPEED_RADPS", 0.5)] * 14,
                "time_scale_s": 2,
                "fast_demo_path": True,
                "whole_body_split": True,
            },
            mode=safe_motion_mode(),
            timeout_s=20.0,
        )
        require_done(result)
        return

    result = submit_task(
        "body.move_whole_body_pose",
        {
            "pose": pose,
            "source_script": source_script,
            "source_json": str(json_path),
            "resolved_json": str(resolve_data_path(json_path)),
            "head_joint_names": HEAD_KEYS,
            "waist_joint_names": WAIST_KEYS,
            "left_arm_joint_names": LEFT_ARM_KEYS,
            "right_arm_joint_names": RIGHT_ARM_KEYS,
            "head_rad": head,
            "waist_rad": waist,
            "left_arm_rad": left,
            "right_arm_rad": right,
            "head_speed_radps": env_float("G2_WXF_FAST_HEAD_SPEED_RADPS", 0.5),
            "waist_speed_radps": env_float("G2_WXF_FAST_WAIST_SPEED_RADPS", 1.0),
            "arm_speed_radps": env_float("G2_WXF_FAST_ARM_SPEED_RADPS", 0.5),
            "inter_command_delay_s": env_float("G2_WXF_FAST_BODY_INTER_COMMAND_DELAY_S", 0.0),
            "settle_s": env_float("G2_WXF_FAST_BODY_SETTLE_S", 0.0),
            "sync_requested": bool(sync_requested),
            "fast_demo_path": True,
        },
        mode=safe_motion_mode(),
        timeout_s=20.0,
    )
    require_done(result)


def run_gripper(action: str, source_script: str, targets: dict[str, float] | None = None) -> None:
    command = "gripper.open" if action == "open" else "gripper.close"
    targets = targets or {"right": -0.785 if action == "open" else 0.0, "left": -0.785 if action == "open" else 0.0}
    force_sequential = env_flag("G2_WXF_FAST_GRIPPER_FORCE_SEQUENTIAL", True)
    inter_side_delay_s = env_float("G2_WXF_FAST_GRIPPER_INTER_SIDE_DELAY_S", 0.15)
    post_wait_s = env_float("G2_WXF_FAST_GRIPPER_POST_WAIT_S", 0.30)
    if not force_sequential and set(targets) == {"left", "right"} and float(targets["left"]) == float(targets["right"]):
        result = submit_task(
            command,
            {
                "side": "both",
                "target_position": float(targets["left"]),
                "target_type": "omnipicker",
                "inter_side_delay_s": inter_side_delay_s,
                "source_script": source_script,
                "fast_demo_path": True,
            },
            mode=safe_motion_mode(),
            timeout_s=5.0,
        )
        require_done(result)
        if post_wait_s > 0:
            time.sleep(post_wait_s)
        return
    for side, target_position in targets.items():
        result = submit_task(
            command,
            {
                "side": side,
                "target_position": float(target_position),
                "target_type": "omnipicker",
                "source_script": source_script,
            },
            mode=safe_motion_mode(),
            timeout_s=5.0,
        )
        require_done(result)
        if inter_side_delay_s > 0:
            time.sleep(inter_side_delay_s)
    if post_wait_s > 0:
        time.sleep(post_wait_s)


def run_ee_offsets(source_script: str, offset_l: Iterable[float], offset_r: Iterable[float]) -> None:
    left = tuple(float(v) for v in offset_l)
    right = tuple(float(v) for v in offset_r)
    if len(left) != 3 or len(right) != 3:
        raise ValueError("offset must contain exactly dx, dy, dz")
    result = submit_task(
        "ee.relative_offset_dual",
        {
            "left_offset_m": list(left),
            "right_offset_m": list(right),
            "frame": "tool",
            "max_step_m": env_float("G2_WXF_FAST_EE_MAX_STEP_M", 0.0005),
            "rate_hz": env_float("G2_WXF_FAST_EE_RATE_HZ", 100.0),
            "life_time_s": env_float("G2_WXF_FAST_EE_LIFE_TIME_S", 0.02),
            "inter_side_delay_s": env_float("G2_WXF_FAST_EE_INTER_SIDE_DELAY_S", 0.0),
            "use_both_group": env_flag("G2_WXF_FAST_EE_USE_BOTH_GROUP", True),
            "source_script": source_script,
            "fast_demo_path": True,
        },
        mode=safe_motion_mode(),
        timeout_s=10.0,
    )
    require_done(result)


def run_nav_waypoints(source_script: str, waypoints: list[dict[str, Any]]) -> None:
    for item in waypoints:
        nav_timeout_s, client_timeout_s = nav_timeouts_from_env()
        result = submit_task(
            "nav.goto_pose",
            {
                "source_script": source_script,
                "map_id": "waypoints-json-index",
                "waypoint_index": item.get("index"),
                "high_precision": bool(item.get("high_precision", False)),
                "allow_estop_pedal_fault": env_flag("G2_WXF_ALLOW_ESTOP_PEDAL_FAULT", False),
                "nav_timeout_s": nav_timeout_s,
                "startup_timeout_s": env_float("G2_WXF_NAV_STARTUP_TIMEOUT_S", 10.0),
                "poll_interval_s": env_float("G2_WXF_NAV_POLL_INTERVAL_S", 0.5),
                "no_progress_timeout_s": env_float("G2_WXF_NAV_NO_PROGRESS_TIMEOUT_S", 45.0),
                "progress_min_distance_m": env_float("G2_WXF_NAV_PROGRESS_MIN_DISTANCE_M", 0.03),
                "progress_min_yaw_rad": env_float("G2_WXF_NAV_PROGRESS_MIN_YAW_RAD", 0.05),
                "progress_min_speed_mps": env_float("G2_WXF_NAV_PROGRESS_MIN_SPEED_MPS", 0.02),
                "x_m": float(item.get("x_m", 0.0)),
                "y_m": float(item.get("y_m", 0.0)),
                "yaw_rad": float(item.get("yaw_rad", 0.0)),
                "tolerance_xy_m": 0.05 if item.get("high_precision") else 0.10,
                "tolerance_yaw_rad": 0.10 if item.get("high_precision") else 0.20,
                "speed_profile": "slow" if item.get("high_precision") else "normal",
                "note": "placeholder dry-run for old RobotController.go(index); no chassis motion",
            },
            mode=safe_motion_mode(),
            timeout_s=client_timeout_s,
        )
        require_done(result)


def run_nav_forward(source_script: str, dist_m: float, speed: float | None = None) -> None:
    nav_timeout_s, client_timeout_s = nav_timeouts_from_env()
    result = submit_task(
        "nav.goto_pose",
        {
            "source_script": source_script,
            "map_id": "relative-placeholder",
            "x_m": float(dist_m),
            "y_m": 0.0,
            "yaw_rad": 0.0,
            "speed_profile": "normal",
            "requested_speed_mps": speed,
            "nav_timeout_s": nav_timeout_s,
            "startup_timeout_s": env_float("G2_WXF_NAV_STARTUP_TIMEOUT_S", 10.0),
            "poll_interval_s": env_float("G2_WXF_NAV_POLL_INTERVAL_S", 0.5),
            "no_progress_timeout_s": env_float("G2_WXF_NAV_NO_PROGRESS_TIMEOUT_S", 45.0),
            "progress_min_distance_m": env_float("G2_WXF_NAV_PROGRESS_MIN_DISTANCE_M", 0.03),
            "progress_min_yaw_rad": env_float("G2_WXF_NAV_PROGRESS_MIN_YAW_RAD", 0.05),
            "progress_min_speed_mps": env_float("G2_WXF_NAV_PROGRESS_MIN_SPEED_MPS", 0.02),
            "note": "placeholder dry-run for old move_forward; no chassis motion",
        },
        mode=safe_motion_mode(),
        timeout_s=client_timeout_s,
    )
    require_done(result)


def run_waist_correction(source_script: str, result_json: str = "yolo_depth_result.json") -> None:
    result_path, data = load_yolo_result_json(result_json)
    target_delta = float(data["slope"]["angle_rad"])
    result = submit_task(
        "waist.move_named_pose",
        {
            "pose": "yolo_correct_waist_delta",
            "source_script": source_script,
            "source_result_json": str(result_path),
            "target_joint": "idx05_body_joint5",
            "delta_rad": -target_delta,
            "original_target_delta_rad": target_delta,
            "joint_velocities_radps": [0.3] * 5,
        },
        mode=safe_motion_mode(),
        timeout_s=15.0,
    )
    require_done(result)


def fetch_gateway_snapshot(camera_id: str, output_path: str | os.PathLike[str], timeout_s: float = 5.0) -> Path:
    url = f"{DEFAULT_HTTP_URL}/api/cameras/{camera_id}/snapshot.jpg"
    target = Path(output_path)
    request = Request(url, headers={"Accept": "image/jpeg"})
    try:
        with urlopen(request, timeout=timeout_s) as response:
            data = response.read()
    except URLError as exc:
        raise RuntimeError(f"failed to fetch gateway camera snapshot: {url}: {exc}") from exc
    target.write_bytes(data)
    print(f"saved {camera_id} snapshot: {target} ({len(data)} bytes)")
    return target


def fetch_gateway_raw_depth(output_path: str | os.PathLike[str], timeout_s: float = 5.0) -> Path:
    url = f"{DEFAULT_HTTP_URL}/api/cameras/head_depth/raw"
    target = Path(output_path)
    request = Request(url, headers={"Accept": "application/octet-stream"})
    try:
        with urlopen(request, timeout=timeout_s) as response:
            data = response.read()
    except URLError as exc:
        raise RuntimeError(f"failed to fetch gateway head depth raw frame: {url}: {exc}") from exc
    target.write_bytes(data)
    print(f"saved head_depth raw: {target} ({len(data)} bytes)")
    return target


def record_gateway_snapshots(camera_id: str = "head_rgb", interval_s: float = 0.5, out_dir: str = "images") -> None:
    out = Path(out_dir)
    if not out.is_absolute():
        out = Path.cwd() / out
    out.mkdir(parents=True, exist_ok=True)
    count = 0
    try:
        while True:
            count += 1
            fetch_gateway_snapshot(camera_id, out / f"{camera_id}_{time.strftime('%Y%m%d_%H%M%S')}_{count:06d}.jpg")
            time.sleep(interval_s)
    except KeyboardInterrupt:
        print(f"stopped, saved {count} frames")


class RobotController:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.source_script = kwargs.pop("source_script", "robot_controller.py")

    def go(self, index: int, high_precision: bool = False, **kwargs: Any) -> None:
        run_nav_waypoints(self.source_script, [{"index": int(index), "high_precision": bool(high_precision)}])

    def move_forward(self, dist_m: float, speed: float | None = None, **kwargs: Any) -> None:
        run_nav_forward(self.source_script, float(dist_m), speed=speed)

    def move_backward(self, dist_m: float, speed: float | None = None, **kwargs: Any) -> None:
        run_nav_forward(self.source_script, -float(dist_m), speed=speed)


class EndEffectorController:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.source_script = kwargs.pop("source_script", "end_effector_controller.py")

    def adjust_arms_relative(self, offset_l=(0.0, 0.0, 0.0), offset_r=(0.0, 0.0, 0.0)) -> None:
        run_ee_offsets(self.source_script, offset_l, offset_r)


def block_unsupported(source_script: str, reason: str) -> int:
    print(f"BLOCKED migrated wrapper: {source_script}")
    print(reason)
    try:
        submit_task(
            "system.read_status",
            {"source_script": source_script, "blocked_reason": reason},
            mode="mock",
            timeout_s=5.0,
            preflight=os.environ.get("G2_WXF_GATEWAY_PREFLIGHT", "require"),
        )
    except Exception as exc:
        print(f"gateway smoke also failed: {type(exc).__name__}: {exc}")
    return 2


def _safe_path_for_sequence(script_dir: Path, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = script_dir / path
    resolved = path.resolve()
    if ROOT not in resolved.parents and resolved != ROOT:
        raise ValueError(f"path escapes migrated workspace: {raw}")
    return resolved


def classify_sequence_command(script_dir: Path, task_entry: str) -> tuple[str, list[str], str]:
    parts = shlex.split(task_entry)
    if not parts:
        return "empty", parts, "empty"
    exe = parts[0]
    if exe in {"cp", "mv"}:
        return "local_file_op", parts, "local copy/move"
    if exe.startswith("yolo-env/"):
        return "vision_python", parts, "vision script through yolo virtualenv"
    if exe.endswith(".py"):
        try:
            target = _safe_path_for_sequence(script_dir, exe)
        except ValueError as exc:
            return "blocked_external", parts, str(exc)
        return "local_python" if target.exists() else "missing_local", parts, str(target)
    if exe in {"python", "python3"} or exe.endswith("/python") or exe.endswith("/python3"):
        if len(parts) < 2:
            return "blocked_unknown", parts, "missing python script"
        try:
            target = _safe_path_for_sequence(script_dir, parts[1])
        except ValueError as exc:
            return "blocked_external", parts, str(exc)
        return "local_python" if target.exists() else "missing_local", parts, str(target)
    return "blocked_unknown", parts, "unknown command"


def _sequence_python_target(script_dir: Path, parts: list[str]) -> tuple[Path, list[str]]:
    if parts[0].endswith(".py"):
        return _safe_path_for_sequence(script_dir, parts[0]), parts[1:]
    return _safe_path_for_sequence(script_dir, parts[1]), parts[2:]


def _source_script_from_target(target: Path) -> str:
    try:
        return target.relative_to(ROOT).as_posix()
    except ValueError:
        return target.name


def _sequence_result_json(base: Path) -> dict[str, Any]:
    result_path, data = load_yolo_result_json("yolo_depth_result.json", base=base)
    if not isinstance(data, dict):
        raise ValueError(f"invalid yolo result JSON: {result_path}")
    return data


def _sequence_depth_pair(base: Path) -> tuple[float, float]:
    data = _sequence_result_json(base)
    return float(data["depth"]["point1_center_mm"]), float(data["depth"]["point2_center_mm"])


def _sequence_horizontal_px(base: Path) -> float:
    data = _sequence_result_json(base)
    return float(data["offset"]["horizontal_offset_px"])


def _run_checked_depth_offset(base: Path, source_script: str, bias_a: float, bias_b: float, travel_m: float) -> None:
    point1, point2 = _sequence_depth_pair(base)
    print(f"read yolo_depth_result depth: point1={point1}, point2={point2}")
    if point1 - point2 > 100 or point2 - point1 > 100:
        raise SystemExit(1)
    depth_offset = (point1 + point2 - bias_a - bias_b) * travel_m / ((bias_a + 42.0) + (bias_b + 40.0) - bias_a - bias_b)
    run_ee_offsets(source_script, (depth_offset, 0.0, 0.0), (depth_offset, 0.0, 0.0))


def _run_fast_sequence_python(base: Path, target: Path, args: list[str]) -> bool:
    source_script = _source_script_from_target(target)
    name = target.name
    rel = source_script

    if rel == "interaction/play_tts_cli.py":
        text_args = [arg for arg in args if not arg.startswith("--")]
        text = " ".join(text_args).strip()
        if env_flag("G2_WXF_FAST_SKIP_TTS", False):
            print(f"# fast_skip_tts: {text}", flush=True)
            return True
        result = submit_task(
            "interaction.play_tts",
            {"text": text, "post_play_wait_s": 0.0, "source_script": source_script, "fast_demo_path": True},
            mode=safe_motion_mode(),
            timeout_s=8.0,
        )
        require_done(result)
        return True

    if name == "move_whole_body_by_json.py":
        json_path = args[0] if args else "../positions/arm_default.json"
        run_whole_body_json(json_path, source_script=source_script)
        return True

    if name == "move_arm_by_json.py" or name.startswith("move_arm_by_json"):
        json_path = args[0] if args else "../positions/arm_default.json"
        run_arm_json(json_path, source_script=source_script)
        return True

    if name == "correct_waist.py":
        run_waist_correction(source_script)
        return True

    if name == "move_ee_pose_right_half.py":
        run_gripper("open", source_script=source_script, targets={"right": -0.05, "left": 0.0})
        return True

    if name == "move_ee_pose_open_05.py":
        run_gripper("open", source_script=source_script, targets={"right": -0.05, "left": -0.05})
        return True

    if name == "move_ee_pose_open_2.py":
        run_gripper("open", source_script=source_script, targets=None)
        # Final release is visually critical. If the left tool does not
        # visibly open after the normal two-side command, resend left only
        # so left_tool is the last gripper command before pull-back.
        if env_flag("G2_WXF_FINAL_LEFT_OPEN_RETRY", True):
            delay_s = env_float("G2_WXF_FINAL_LEFT_OPEN_RETRY_DELAY_S", 0.10)
            if delay_s > 0:
                time.sleep(delay_s)
            result = submit_task(
                "gripper.open",
                {
                    "side": "left",
                    "target_position": -0.785,
                    "target_type": "omnipicker",
                    "source_script": f"{source_script}:left_retry",
                    "fast_demo_path": True,
                },
                mode=safe_motion_mode(),
                timeout_s=5.0,
            )
            require_done(result)
        return True

    if name == "move_ee_pose_close_2.py":
        run_gripper("close", source_script=source_script, targets=None)
        return True

    static_offsets: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {
        "offset_move_backward_002.py": ((-0.02, 0.0, 0.0), (-0.02, 0.0, 0.0)),
        "offset_move_car_grab.py": ((0.0, -0.10, 0.0), (0.0, 0.10, 0.0)),
        "offset_move_downpickb.py": ((0.0, 0.0, -0.03), (0.0, 0.0, -0.03)),
        "offset_move_downward_002.py": ((0.0, 0.0, -0.02), (0.0, 0.0, -0.02)),
        "offset_move_downward_004.py": ((0.0, 0.0, -0.04), (0.0, 0.0, -0.04)),
        "offset_move_forward_001.py": ((0.01, 0.0, 0.0), (0.01, 0.0, 0.0)),
        "offset_move_forward_002.py": ((0.02, 0.0, 0.0), (0.02, 0.0, 0.0)),
        "offset_move_forward_006.py": ((0.06, 0.0, 0.0), (0.06, 0.0, 0.0)),
        "offset_move_forward_009.py": ((0.09, 0.0, 0.0), (0.09, 0.0, 0.0)),
        "offset_move_left_002.py": ((0.0, 0.02, 0.0), (0.0, 0.02, 0.0)),
        "offset_move_left_025.py": ((0.0, 0.04, 0.0), (0.0, 0.04, 0.0)),
        "offset_move_pull.py": ((-0.16, 0.0, 0.0), (-0.16, 0.0, 0.0)),
        "offset_move_pull_back.py": ((-0.14, 0.0, 0.0), (-0.14, 0.0, 0.0)),
        "offset_move_up.py": ((0.0, 0.0, 0.20), (0.0, 0.0, 0.20)),
        "offset_move_upward_015.py": ((0.0, 0.0, 0.15), (0.0, 0.0, 0.15)),
    }
    if name in static_offsets:
        left, right = static_offsets[name]
        run_ee_offsets(source_script, left, right)
        return True

    if name == "offset_move_horizon.py":
        offset_y = _sequence_horizontal_px(base) * (-0.2) / 100.0 + 0.03
        run_ee_offsets(source_script, (0.0, offset_y, 0.0), (0.0, offset_y, 0.0))
        return True

    if name == "offset_move_horizon_b.py":
        offset_y = _sequence_horizontal_px(base) * (-0.2) / 100.0
        run_ee_offsets(source_script, (0.0, offset_y, 0.0), (0.0, offset_y, 0.0))
        return True

    if name == "offset_move_vertical.py":
        _run_checked_depth_offset(base, source_script, 633.0, 640.0, 0.05)
        return True

    if name == "offset_move_vertical_b.py":
        point1, point2 = _sequence_depth_pair(base)
        print(f"read yolo_depth_result depth: point1={point1}, point2={point2}")
        if point1 - point2 > 100 or point2 - point1 > 100:
            raise SystemExit(1)
        depth_offset = (point1 + point2 - 684.0 - 688.0) * 0.085 / (738.0 + 734.0 - 684.0 - 688.0)
        run_ee_offsets(source_script, (depth_offset, 0.0, 0.0), (depth_offset, 0.0, 0.0))
        return True

    if name == "offset_move_push_grab.py":
        horizontal_offset_m = _sequence_horizontal_px(base) / 1000.0
        run_ee_offsets(source_script, (0.0, horizontal_offset_m, 0.0), (0.0, horizontal_offset_m, 0.0))
        run_ee_offsets(source_script, (0.09, 0.0, 0.0), (0.09, 0.0, 0.0))
        return True

    return False


def _fast_sequence_label(base: Path, kind: str, parts: list[str]) -> str | None:
    if kind != "local_python":
        return None
    try:
        target, _args = _sequence_python_target(base, parts)
    except Exception:
        return None
    fast_names = {
        "correct_waist.py",
        "move_arm_by_json.py",
        "move_ee_pose_close_2.py",
        "move_ee_pose_open_05.py",
        "move_ee_pose_open_2.py",
        "move_ee_pose_right_half.py",
        "move_whole_body_by_json.py",
        "offset_move_backward_002.py",
        "offset_move_car_grab.py",
        "offset_move_downpickb.py",
        "offset_move_downward_002.py",
        "offset_move_downward_004.py",
        "offset_move_forward_001.py",
        "offset_move_forward_002.py",
        "offset_move_forward_006.py",
        "offset_move_forward_009.py",
        "offset_move_horizon.py",
        "offset_move_horizon_b.py",
        "offset_move_left_002.py",
        "offset_move_left_025.py",
        "offset_move_pull.py",
        "offset_move_pull_back.py",
        "offset_move_push_grab.py",
        "offset_move_up.py",
        "offset_move_upward_015.py",
        "offset_move_vertical.py",
        "offset_move_vertical_b.py",
    }
    if _source_script_from_target(target) == "interaction/play_tts_cli.py":
        return "MQTT interaction.play_tts"
    if target.name in fast_names or target.name.startswith("move_arm_by_json"):
        return f"MQTT {_source_script_from_target(target)}"
    return None


def run_sequence(name: str, sequence: list[str], script_dir: str | os.PathLike[str], execute: bool = False) -> int:
    base = Path(script_dir).resolve()
    sequence_timeout_s = env_float("G2_WXF_SEQUENCE_TIMEOUT_S", 0.0) if execute else 0.0
    if execute and sequence_timeout_s > 0.0 and not os.environ.get(SEQUENCE_DEADLINE_ENV):
        os.environ[SEQUENCE_DEADLINE_ENV] = f"{time.time() + sequence_timeout_s:.6f}"
    print(f"# {name}")
    print(f"# steps={len(sequence)}, mode={'execute' if execute else 'dry-run plan'}")
    if execute and sequence_timeout_s > 0.0:
        print(f"# sequence_timeout_s={sequence_timeout_s:.1f}")
    for index, entry in enumerate(sequence, 1):
        kind, parts, reason = classify_sequence_command(base, entry)
        fast_label = _fast_sequence_label(base, kind, parts)
        display_kind = "fast_inline" if fast_label else kind
        display_reason = fast_label or reason
        print(f"[{index:02d}/{len(sequence):02d}] {display_kind}: {entry} ({display_reason})")
        if not execute:
            continue
        require_sequence_budget(f"step {index}: {entry}", min_remaining_s=1.0)
        if kind in {"blocked_external", "blocked_unknown", "empty", "missing_local"}:
            print("blocked by migrated sequence runner")
            return 1
        if kind == "local_file_op":
            if len(parts) != 3:
                print("only two-argument cp/mv is allowed")
                return 1
            src = _safe_path_for_sequence(base, parts[1])
            dst = _safe_path_for_sequence(base, parts[2])
            if parts[0] == "cp":
                shutil.copy2(src, dst)
            else:
                shutil.move(src, dst)
            continue
        if kind == "local_python":
            target, script_args = _sequence_python_target(base, parts)
            if _run_fast_sequence_python(base, target, script_args):
                require_sequence_budget(f"after step {index}: {entry}", min_remaining_s=0.0)
                continue
            cmd = [sys.executable, str(target), *script_args]
        elif kind == "vision_python":
            # Keep the venv entrypoint path instead of resolving symlinks.
            # Resolving yolo-env/bin/python can collapse to /usr/bin/python3.10
            # and lose the virtualenv site-packages that contain ultralytics.
            venv_python = base / parts[0]
            if not venv_python.exists():
                venv_python = ORIGINAL_ROOT / "yolo" / "yolo-env" / "bin" / "python"
            target = _safe_path_for_sequence(base, parts[1])
            cmd = [str(venv_python), str(target), *parts[2:]]
        else:
            return 1
        rc = subprocess.run(cmd, cwd=base).returncode
        if rc != 0:
            print(f"step failed rc={rc}: {entry}")
            return rc
        require_sequence_budget(f"after step {index}: {entry}", min_remaining_s=0.0)
    return 0


def gateway_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One-shot G2 gateway MQTT task client")
    parser.add_argument("--command", default="gdk.read_power_state")
    parser.add_argument("--mode", default="read_only")
    parser.add_argument("--args-json", default="{}")
    parser.add_argument("--timeout-s", type=float, default=15.0)
    parser.add_argument("--confirm-physical", action="store_true")
    parser.add_argument("--preflight", choices=sorted(PREFLIGHT_POLICIES), default="require")
    args = parser.parse_args(argv)
    payload_args = json.loads(args.args_json)
    if not isinstance(payload_args, dict):
        raise ValueError("--args-json must decode to an object")
    result = submit_task(
        args.command,
        payload_args,
        mode=args.mode,
        timeout_s=args.timeout_s,
        preflight=args.preflight,
        confirm_physical=args.confirm_physical,
    )
    return 0 if result.get("state") == "DONE" else 1


HEAD_KEYS = ["idx11_head_joint1", "idx12_head_joint2", "idx13_head_joint3"]
WAIST_KEYS = ["idx01_body_joint1", "idx02_body_joint2", "idx03_body_joint3", "idx04_body_joint4", "idx05_body_joint5"]
LEFT_ARM_KEYS = [
    "idx21_arm_l_joint1", "idx22_arm_l_joint2", "idx23_arm_l_joint3", "idx24_arm_l_joint4",
    "idx25_arm_l_joint5", "idx26_arm_l_joint6", "idx27_arm_l_joint7",
]
RIGHT_ARM_KEYS = [
    "idx61_arm_r_joint1", "idx62_arm_r_joint2", "idx63_arm_r_joint3", "idx64_arm_r_joint4",
    "idx65_arm_r_joint5", "idx66_arm_r_joint6", "idx67_arm_r_joint7",
]
