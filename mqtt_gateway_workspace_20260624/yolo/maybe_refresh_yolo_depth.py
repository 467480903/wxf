#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conditionally reuse a stable YOLO result instead of recapturing a second pass.

This helper is intentionally conservative. It preserves the original visual
function by running the same cam_get_head.py + yolo_depth.py refresh whenever the
current result is missing, malformed, or outside tight stability thresholds.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
RESULT_JSON = BASE / "yolo_depth_result.json"


def _float_at(data: dict[str, Any], dotted: str) -> float:
    cur: Any = data
    for part in dotted.split("."):
        if part.endswith("]") and "[" in part:
            name, index_text = part[:-1].split("[", 1)
            if name:
                if not isinstance(cur, dict) or name not in cur:
                    raise KeyError(dotted)
                cur = cur[name]
            cur = cur[int(index_text)]
            continue
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(dotted)
        cur = cur[part]
    value = float(cur)
    if not math.isfinite(value):
        raise ValueError(dotted)
    return value


def _load_result() -> tuple[dict[str, Any] | None, str | None]:
    if not RESULT_JSON.exists():
        return None, "missing yolo_depth_result.json"
    try:
        data = json.loads(RESULT_JSON.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None, "result JSON is not an object"
        return data, None
    except Exception as exc:
        return None, f"invalid result JSON: {type(exc).__name__}: {exc}"


def _decision(data: dict[str, Any], max_horizontal_px: float, max_slope_deg: float, max_depth_diff_mm: float) -> tuple[bool, str, dict[str, float]]:
    horizontal_px = _float_at(data, "offset.horizontal_offset_px")
    raw_slope_rad = _float_at(data, "slope.angle_rad")
    slope_rad = ((raw_slope_rad + math.pi / 2.0) % math.pi) - math.pi / 2.0
    point1_mm = _float_at(data, "depth.point1_center_mm")
    point2_mm = _float_at(data, "depth.point2_center_mm")
    _float_at(data, "detection.point1.center[0]")
    _float_at(data, "detection.point1.center[1]")
    _float_at(data, "detection.point2.center[0]")
    _float_at(data, "detection.point2.center[1]")

    slope_deg = abs(math.degrees(slope_rad))
    depth_diff_mm = abs(point1_mm - point2_mm)
    metrics = {
        "horizontal_px": horizontal_px,
        "abs_horizontal_px": abs(horizontal_px),
        "raw_slope_deg": math.degrees(raw_slope_rad),
        "normalized_slope_deg": math.degrees(slope_rad),
        "slope_deg": slope_deg,
        "depth_diff_mm": depth_diff_mm,
        "point1_mm": point1_mm,
        "point2_mm": point2_mm,
    }
    problems: list[str] = []
    if abs(horizontal_px) > max_horizontal_px:
        problems.append(f"abs_horizontal_px={abs(horizontal_px):.3f}>{max_horizontal_px:.3f}")
    if slope_deg > max_slope_deg:
        problems.append(f"slope_deg={slope_deg:.3f}>{max_slope_deg:.3f}")
    if depth_diff_mm > max_depth_diff_mm:
        problems.append(f"depth_diff_mm={depth_diff_mm:.3f}>{max_depth_diff_mm:.3f}")
    if problems:
        return False, "; ".join(problems), metrics
    return True, "within stable thresholds", metrics


def _run(cmd: list[str]) -> None:
    print("# vision_second_pass_refresh_cmd: " + " ".join(cmd), flush=True)
    rc = subprocess.run(cmd, cwd=BASE).returncode
    if rc != 0:
        raise SystemExit(rc)


def _refresh(model: str, extra_args: list[str]) -> None:
    started_at = time.time()
    _run([sys.executable, str(BASE / "cam_get_head.py")])
    venv_python = BASE / "yolo-env" / "bin" / "python"
    if not venv_python.exists():
        venv_python = Path("/data/wxf/wxf/yolo/yolo-env/bin/python")
    _run([str(venv_python), str(BASE / "yolo_depth.py"), model, *extra_args])
    if not RESULT_JSON.exists():
        raise SystemExit("vision refresh did not create yolo_depth_result.json")
    if RESULT_JSON.stat().st_mtime < started_at - 0.5:
        raise SystemExit("vision refresh left stale yolo_depth_result.json")
    data, problem = _load_result()
    if problem is not None or data is None:
        raise SystemExit(problem or "invalid refreshed result")


def main() -> int:
    parser = argparse.ArgumentParser(description="Conditionally skip second YOLO pass when first result is already stable")
    parser.add_argument("model", help="YOLO model argument, e.g. shelf.pt")
    parser.add_argument("extra_args", nargs="*", help="extra yolo_depth.py arguments, e.g. 1")
    parser.add_argument("--purpose", default="second_pass", help="log label for this reuse decision")
    parser.add_argument("--max-horizontal-px", type=float, default=float(os.environ.get("G2_WXF_VISION_REUSE_MAX_HORIZONTAL_PX", "2.0")))
    parser.add_argument("--max-slope-deg", type=float, default=float(os.environ.get("G2_WXF_VISION_REUSE_MAX_SLOPE_DEG", "0.5")))
    parser.add_argument("--max-depth-diff-mm", type=float, default=float(os.environ.get("G2_WXF_VISION_REUSE_MAX_DEPTH_DIFF_MM", "60.0")))
    parser.add_argument("--dry-run", action="store_true", help="print the decision without recapturing")
    args = parser.parse_args()

    enabled = os.environ.get("G2_WXF_VISION_SECOND_PASS_REUSE", "1").lower() not in {"0", "false", "no", "off"}
    data, problem = _load_result()
    if not enabled:
        decision_ok = False
        reason = "disabled by G2_WXF_VISION_SECOND_PASS_REUSE"
        metrics: dict[str, float] = {}
    elif data is None:
        decision_ok = False
        reason = problem or "no usable result"
        metrics = {}
    else:
        try:
            decision_ok, reason, metrics = _decision(data, args.max_horizontal_px, args.max_slope_deg, args.max_depth_diff_mm)
        except Exception as exc:
            decision_ok = False
            reason = f"metric extraction failed: {type(exc).__name__}: {exc}"
            metrics = {}

    metric_text = " ".join(f"{key}={value:.3f}" for key, value in metrics.items())
    print(
        f"# vision_second_pass_decision: purpose={args.purpose} reuse={str(decision_ok).lower()} "
        f"reason={reason!r} max_horizontal_px={args.max_horizontal_px:.3f} "
        f"max_slope_deg={args.max_slope_deg:.3f} max_depth_diff_mm={args.max_depth_diff_mm:.3f} {metric_text}".rstrip(),
        flush=True,
    )

    if decision_ok:
        print(f"# vision_second_pass_reuse: purpose={args.purpose} reused yolo_depth_result.json", flush=True)
        return 0
    if args.dry_run:
        print(f"# vision_second_pass_refresh_needed: purpose={args.purpose} dry_run=true", flush=True)
        return 0
    _refresh(args.model, args.extra_args)
    print(f"# vision_second_pass_refresh_done: purpose={args.purpose}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
