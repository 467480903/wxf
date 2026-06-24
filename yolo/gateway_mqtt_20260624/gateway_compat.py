#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers for the migrated yolo scripts."""

from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from gateway_mqtt_client import run_gateway_task


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MODE = os.environ.get("G2_YOLO_GATEWAY_MODE", "dry_run")
DEFAULT_PREFLIGHT = os.environ.get("G2_YOLO_GATEWAY_PREFLIGHT", "require")
DEFAULT_TIMEOUT_S = float(os.environ.get("G2_YOLO_GATEWAY_TIMEOUT_S", "15"))
GATEWAY_HTTP_URL = os.environ.get("G2_GATEWAY_HTTP_URL", "http://127.0.0.1:8767").rstrip("/")


def safe_motion_mode(mode: str | None = None) -> str:
    selected = (mode or DEFAULT_MODE or "dry_run").strip()
    if selected not in {"dry_run", "mock"}:
        raise SystemExit(
            f"当前迁移脚本只允许 dry_run/mock，收到 mode={selected!r}。"
            "真实动作要先在网关侧补 live 能力并由现场确认。"
        )
    return selected


def resolve_original_relative_path(path: str | os.PathLike[str]) -> Path:
    raw = Path(path)
    if raw.is_absolute():
        return raw
    candidates = [
        (Path.cwd() / raw).resolve(),
        (SCRIPT_DIR / raw).resolve(),
        (SCRIPT_DIR.parent / raw).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_json(path: str | os.PathLike[str]) -> dict[str, Any]:
    json_path = resolve_original_relative_path(path)
    if not json_path.exists():
        raise FileNotFoundError(f"找不到 JSON 文件: {json_path}")
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON 顶层必须是对象: {json_path}")
    return data


def extract_values(data: dict[str, Any], keys: list[str]) -> list[float]:
    return [float(data.get(key, 0.0)) for key in keys]


def pose_name_from_path(path: str | os.PathLike[str], prefix: str = "json_pose") -> str:
    stem = Path(path).stem or "unnamed"
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in stem)
    return f"{prefix}_{safe}"


def submit_task(
    command: str,
    args: dict[str, Any],
    mode: str | None = None,
    timeout_s: float | None = None,
    preflight: str | None = None,
) -> dict[str, Any]:
    result = run_gateway_task(
        command=command,
        args=args,
        mode=mode or safe_motion_mode(),
        timeout_s=timeout_s or DEFAULT_TIMEOUT_S,
        preflight=preflight or DEFAULT_PREFLIGHT,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
    return result


def require_done(result: dict[str, Any]) -> None:
    if result.get("state") != "DONE":
        raise SystemExit(1)


def rad_to_deg(value: float) -> float:
    return float(value) * 180.0 / math.pi


def fetch_gateway_snapshot(camera_id: str, output_path: str | os.PathLike[str], timeout_s: float = 5.0) -> Path:
    url = f"{GATEWAY_HTTP_URL}/api/cameras/{camera_id}/snapshot.jpg"
    target = Path(output_path)
    request = Request(url, headers={"Accept": "image/jpeg"})
    try:
        with urlopen(request, timeout=timeout_s) as response:
            data = response.read()
    except URLError as exc:
        raise RuntimeError(f"读取网关相机快照失败: {url}: {exc}") from exc
    if not data:
        raise RuntimeError(f"网关相机快照为空: {url}")
    target.write_bytes(data)
    print(f"已保存 {camera_id} 快照: {target} ({len(data)} bytes)")
    return target


def record_gateway_snapshots(camera_id: str = "head_rgb", interval_s: float = 0.5, out_dir: str = "images") -> None:
    image_dir = SCRIPT_DIR / out_dir
    image_dir.mkdir(parents=True, exist_ok=True)
    frame_count = 0
    print(f"开始从网关 HTTP 相机接口录制 {camera_id}，保存目录: {image_dir}")
    try:
        while True:
            frame_count += 1
            filename = f"{camera_id}_{time.strftime('%Y%m%d_%H%M%S')}_{frame_count:06d}.jpg"
            fetch_gateway_snapshot(camera_id, image_dir / filename)
            time.sleep(interval_s)
    except KeyboardInterrupt:
        print(f"用户中断，共保存 {frame_count} 张")


def default_json_path(*candidates: str) -> str:
    for item in candidates:
        path = resolve_original_relative_path(item)
        if path.exists():
            return str(path)
    print("未找到默认 JSON 文件，请显式传入路径", file=sys.stderr)
    raise SystemExit(1)
