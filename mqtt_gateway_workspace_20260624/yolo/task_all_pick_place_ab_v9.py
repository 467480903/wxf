#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V9 optimized continuous A/B pick-place runner for G2A.

V9 is V8's idle-first navigation profile plus the current G2A flow/throughput
optimizations:

1. place_a/place_b second visual pass is conditional. The child scripts call
   maybe_refresh_yolo_depth.py, which reuses the first YOLO result only when the
   result is already stable and otherwise runs the original second
   cam_get_head.py + yolo_depth.py refresh.
2. place_b uses the current G2A offset_move_vertical_b.py behavior, including
   forward_bias_m = 0.015 and the existing 0.085 m cap.

This top-level wrapper does not hard-code child task internals. It loads the
current child TASK_SEQUENCE from task_all_place_a.py and task_all_place_b.py, so
V9 stays aligned with the active optimized child scripts on this G2A robot.
"""

from __future__ import annotations

import argparse
import os
import runpy
import sys
import time
from pathlib import Path
from typing import Any


for _parent in Path(__file__).resolve().parents:
    _common = _parent / "mqtt_common"
    if _common.is_dir():
        sys.path.insert(0, str(_common))
        break

from mqtt_common import run_sequence


CHILDREN = [
    ("pick_a", "task_all_pick_a.py", "yolo/task_all_pick_a.py"),
    ("place_a", "task_all_place_a.py", "yolo/task_all_place_a.py"),
    ("pick_b", "task_all_pick_b.py", "yolo/task_all_pick_b.py"),
    ("place_b", "task_all_place_b.py", "yolo/task_all_place_b.py"),
]


def _load_child_sequence(script_path: Path) -> list[str]:
    namespace: dict[str, Any] = runpy.run_path(str(script_path), run_name=f"_wxf_v9_{script_path.stem}")
    sequence = namespace.get("TASK_SEQUENCE")
    if not isinstance(sequence, list) or not all(isinstance(item, str) for item in sequence):
        raise RuntimeError(f"{script_path.name} does not expose a valid TASK_SEQUENCE")
    return list(sequence)


def _restore_environment(snapshot: dict[str, str]) -> None:
    os.environ.clear()
    os.environ.update(snapshot)


def _v9_env(name: str, default: str) -> str:
    return os.environ.get(f"G2_WXF_V9_{name}", os.environ.get(f"G2_WXF_V8_{name}", default))


def _apply_v9_profile() -> dict[str, str]:
    """Apply V9 continuity and conditional-vision profile for this process."""
    profile = {
        "G2_WXF_TTS_PRE_PLAY_DELAY_S": _v9_env("TTS_PRE_PLAY_DELAY_S", "0.0"),
        "G2_WXF_NAV_IDLE_STABLE_S": _v9_env("NAV_IDLE_STABLE_S", "0.15"),
        "G2_WXF_NAV_IDLE_WAIT_POLL_S": _v9_env("NAV_IDLE_WAIT_POLL_S", "0.15"),
        "G2_WXF_NAV_BUSY_WAIT_IDLE_BEFORE_RETRY": _v9_env("NAV_BUSY_WAIT_IDLE_BEFORE_RETRY", "1"),
        "G2_WXF_NAV_SKIP_PRE_IDLE_FIRST": _v9_env("NAV_SKIP_PRE_IDLE_FIRST", "0"),
        "G2_WXF_NAV_CANCEL_EXISTING_FIRST": _v9_env("NAV_CANCEL_EXISTING_FIRST", "1"),
        "G2_WXF_NAV_IDLE_WAIT_TIMEOUT_S": _v9_env("NAV_IDLE_WAIT_TIMEOUT_S", "120.0"),
        "G2_WXF_NAV_BUSY_RETRY_DELAY_S": _v9_env("NAV_BUSY_RETRY_DELAY_S", "0.10"),
        "G2_WXF_NAV_POLL_INTERVAL_S": _v9_env("NAV_POLL_INTERVAL_S", "0.15"),
        "G2_WXF_FAST_WHOLE_BODY_SPLIT_DELAY_S": _v9_env("FAST_WHOLE_BODY_SPLIT_DELAY_S", "0.02"),
        "G2_WXF_YOLO_RESIDENT": _v9_env("YOLO_RESIDENT", "1"),
        "G2_WXF_MP3_INLINE": _v9_env("MP3_INLINE", "1"),
        "G2_WXF_VISION_SECOND_PASS_REUSE": _v9_env("VISION_SECOND_PASS_REUSE", "1"),
        "G2_WXF_VISION_REUSE_MAX_HORIZONTAL_PX": _v9_env("VISION_REUSE_MAX_HORIZONTAL_PX", "2.0"),
        "G2_WXF_VISION_REUSE_MAX_SLOPE_DEG": _v9_env("VISION_REUSE_MAX_SLOPE_DEG", "0.5"),
        "G2_WXF_VISION_REUSE_MAX_DEPTH_DIFF_MM": _v9_env("VISION_REUSE_MAX_DEPTH_DIFF_MM", "60.0"),
    }
    os.environ.update(profile)
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V9 optimized MQTT runner for pick A, place A, pick B, and place B"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="execute the full live MQTT sequence; default prints the plan only",
    )
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    profile = _apply_v9_profile()
    print("# yolo/task_all_pick_place_ab_v9.py")
    print(f"# children={len(CHILDREN)}, mode={'execute' if args.execute else 'dry-run plan'}")
    print("# baseline_v8=yolo/task_all_pick_place_ab_v8.py")
    print("# optimization=V8 idle-first navigation + conditional second-pass vision reuse + G2A place_b forward bias")
    for key, value in profile.items():
        print(f"# v9_profile: {key}={value}")

    overall_started_at = time.time()
    for child_index, (label, filename, sequence_name) in enumerate(CHILDREN, 1):
        child_path = base / filename
        if not child_path.exists():
            print(f"missing child script: {child_path}")
            return 1

        env_before_child = dict(os.environ)
        child_started_at = time.time()
        rc = 1
        try:
            sequence = _load_child_sequence(child_path)
            _apply_v9_profile()
            print(
                f"[child {child_index:02d}/{len(CHILDREN):02d}] {label}: "
                f"{filename} steps={len(sequence)}",
                flush=True,
            )
            rc = run_sequence(sequence_name, sequence, base, execute=args.execute)
        finally:
            _restore_environment(env_before_child)

        child_duration_s = time.time() - child_started_at
        status = "done" if rc == 0 else "failed"
        print(
            f"# child_timing: index={child_index:02d}/{len(CHILDREN):02d} "
            f"label={label} status={status} duration_s={child_duration_s:.3f}",
            flush=True,
        )
        if rc != 0:
            return rc

    total_duration_s = time.time() - overall_started_at
    print(f"# v9_total_timing: status=done duration_s={total_duration_s:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
