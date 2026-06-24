#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Business-facing shelf detection guard API.

Customer scripts should use this layer when they want a simple decision:

    ok -> it is reasonable to continue the next business step
    not ok -> stop the sequence and show the reason

This module does not import GDK and does not publish robot motion commands. It
calls `detect_once()`, which captures RGB/depth through Gateway HTTP and sends
the image pair to the always-on MQTT YOLO service.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from yolo_detect_gateway_client import detect_once


class ShelfDetectError(RuntimeError):
    """Raised when shelf detection did not produce a safe usable result."""

    def __init__(self, reason: str, summary: dict[str, Any]) -> None:
        super().__init__(reason)
        self.summary = summary


DEFAULT_PROFILE_PATH = "shelf_guard_profiles.json"


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _point_payload(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    center = value.get("center")
    if not isinstance(center, list) or len(center) != 2:
        return None
    return {
        "label": value.get("label"),
        "center": [round(float(center[0]), 2), round(float(center[1]), 2)],
    }


def summarize_detection_result(result: dict[str, Any]) -> dict[str, Any]:
    """Convert the raw MQTT result JSON into a compact business payload."""

    detection = result.get("detection") if isinstance(result.get("detection"), dict) else {}
    offset = result.get("offset") if isinstance(result.get("offset"), dict) else {}
    slope = result.get("slope") if isinstance(result.get("slope"), dict) else {}
    depth = result.get("depth") if isinstance(result.get("depth"), dict) else {}
    server = result.get("server") if isinstance(result.get("server"), dict) else {}

    point1 = _point_payload(detection.get("point1"))
    point2 = _point_payload(detection.get("point2"))
    horizontal_offset_px = _as_float(offset.get("horizontal_offset_px"))
    angle_deg = _as_float(slope.get("angle_deg"))
    center_depth_mm = _as_float(depth.get("center_mm"))

    return {
        "ok": result.get("status") == "success",
        "reason": "" if result.get("status") == "success" else str(result.get("error") or "detect status is not success"),
        "status": result.get("status"),
        "request_id": result.get("request_id"),
        "point1": point1,
        "point2": point2,
        "line_center": offset.get("line_center"),
        "horizontal_offset_px": None if horizontal_offset_px is None else round(horizontal_offset_px, 2),
        "direction": offset.get("direction"),
        "angle_deg": None if angle_deg is None else round(angle_deg, 3),
        "center_depth_mm": None if center_depth_mm is None else round(center_depth_mm, 1),
        "server_latency_ms": server.get("latency_ms"),
        "server_work_dir": server.get("work_dir"),
        "raw_result": result,
    }


def validate_summary(
    summary: dict[str, Any],
    *,
    max_abs_offset_px: float | None = None,
    max_abs_angle_deg: float | None = None,
    min_center_depth_mm: float | None = None,
    max_center_depth_mm: float | None = None,
) -> dict[str, Any]:
    """Apply optional business thresholds to a compact detection summary."""

    reasons: list[str] = []
    if not summary.get("ok"):
        reasons.append(str(summary.get("reason") or "detect failed"))
    if summary.get("point1") is None or summary.get("point2") is None:
        reasons.append("missing point1 or point2")

    horizontal_offset_px = _as_float(summary.get("horizontal_offset_px"))
    if max_abs_offset_px is not None:
        if horizontal_offset_px is None:
            reasons.append("missing horizontal_offset_px")
        elif abs(horizontal_offset_px) > float(max_abs_offset_px):
            reasons.append(f"abs(horizontal_offset_px) {abs(horizontal_offset_px):.2f} > {float(max_abs_offset_px):.2f}")

    angle_deg = _as_float(summary.get("angle_deg"))
    if max_abs_angle_deg is not None:
        if angle_deg is None:
            reasons.append("missing angle_deg")
        elif abs(angle_deg) > float(max_abs_angle_deg):
            reasons.append(f"abs(angle_deg) {abs(angle_deg):.3f} > {float(max_abs_angle_deg):.3f}")

    center_depth_mm = _as_float(summary.get("center_depth_mm"))
    if min_center_depth_mm is not None:
        if center_depth_mm is None:
            reasons.append("missing center_depth_mm")
        elif center_depth_mm < float(min_center_depth_mm):
            reasons.append(f"center_depth_mm {center_depth_mm:.1f} < {float(min_center_depth_mm):.1f}")
    if max_center_depth_mm is not None:
        if center_depth_mm is None:
            reasons.append("missing center_depth_mm")
        elif center_depth_mm > float(max_center_depth_mm):
            reasons.append(f"center_depth_mm {center_depth_mm:.1f} > {float(max_center_depth_mm):.1f}")

    summary["ok"] = not reasons
    summary["reason"] = "" if not reasons else "; ".join(reasons)
    return summary


def load_guard_profiles(profile_path: str | Path = DEFAULT_PROFILE_PATH) -> dict[str, Any]:
    """Load the guard profile JSON file."""

    path = Path(profile_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"guard profile file must contain a JSON object: {path}")
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError(f"guard profile file missing profiles object: {path}")
    return payload


def load_guard_profile(
    profile_name: str,
    *,
    profile_path: str | Path = DEFAULT_PROFILE_PATH,
    allow_unconfirmed_profile: bool = False,
) -> dict[str, Any]:
    """Load one named guard profile and enforce confirmation metadata."""

    payload = load_guard_profiles(profile_path)
    profiles = payload["profiles"]
    profile = profiles.get(profile_name)
    if not isinstance(profile, dict):
        available = ", ".join(sorted(str(name) for name in profiles))
        raise KeyError(f"unknown shelf guard profile {profile_name!r}; available: {available}")
    if not profile.get("confirmed_for_motion", False) and not allow_unconfirmed_profile:
        raise ValueError(
            f"shelf guard profile {profile_name!r} is not confirmed_for_motion; "
            "set confirmed_for_motion=true after process owner approval"
        )
    return profile


def profile_thresholds(profile: dict[str, Any]) -> dict[str, float | None]:
    """Extract validate_summary threshold kwargs from a profile."""

    thresholds = profile.get("thresholds")
    if thresholds is None:
        thresholds = {}
    if not isinstance(thresholds, dict):
        raise ValueError("profile thresholds must be an object")
    names = (
        "max_abs_offset_px",
        "max_abs_angle_deg",
        "min_center_depth_mm",
        "max_center_depth_mm",
    )
    result: dict[str, float | None] = {}
    for name in names:
        value = thresholds.get(name)
        result[name] = None if value is None else float(value)
    return result


def detect_shelf(
    *,
    gateway_url: str = "http://127.0.0.1:8767",
    broker: str = "127.0.0.1",
    port: int = 1883,
    http_timeout_s: float = 15.0,
    timeout_s: float = 180.0,
    capture_dir: str = "captures",
    max_abs_offset_px: float | None = None,
    max_abs_angle_deg: float | None = None,
    min_center_depth_mm: float | None = None,
    max_center_depth_mm: float | None = None,
    raise_on_error: bool = True,
    verbose: bool = False,
) -> dict[str, Any]:
    """Capture and detect shelf points, returning a guard-friendly summary."""

    raw_result = detect_once(
        gateway_url=gateway_url,
        broker=broker,
        port=port,
        http_timeout_s=http_timeout_s,
        timeout_s=timeout_s,
        capture_dir=capture_dir,
        raise_on_error=False,
        verbose=verbose,
    )
    summary = summarize_detection_result(raw_result)
    validate_summary(
        summary,
        max_abs_offset_px=max_abs_offset_px,
        max_abs_angle_deg=max_abs_angle_deg,
        min_center_depth_mm=min_center_depth_mm,
        max_center_depth_mm=max_center_depth_mm,
    )
    if raise_on_error and not summary["ok"]:
        raise ShelfDetectError(str(summary["reason"]), summary)
    return summary


def detect_shelf_with_profile(
    profile_name: str = "observe_only",
    *,
    profile_path: str | Path = DEFAULT_PROFILE_PATH,
    allow_unconfirmed_profile: bool = False,
    gateway_url: str = "http://127.0.0.1:8767",
    broker: str = "127.0.0.1",
    port: int = 1883,
    http_timeout_s: float = 15.0,
    timeout_s: float = 180.0,
    capture_dir: str = "captures",
    raise_on_error: bool = True,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run shelf detection using a named guard profile."""

    profile = load_guard_profile(
        profile_name,
        profile_path=profile_path,
        allow_unconfirmed_profile=allow_unconfirmed_profile,
    )
    thresholds = profile_thresholds(profile)
    summary = detect_shelf(
        gateway_url=gateway_url,
        broker=broker,
        port=port,
        http_timeout_s=http_timeout_s,
        timeout_s=timeout_s,
        capture_dir=capture_dir,
        raise_on_error=raise_on_error,
        verbose=verbose,
        **thresholds,
    )
    summary["profile_name"] = profile_name
    summary["profile_description"] = profile.get("description", "")
    return summary
