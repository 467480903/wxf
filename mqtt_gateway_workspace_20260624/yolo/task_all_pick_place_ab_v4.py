#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V4 low-risk continuous A/B pick-place runner.

V4 keeps V3's action order and software waits, then enables the resident YOLO
worker for yolo_depth.py calls. The worker caches model objects only; it does
not skip camera captures, YOLO detections, depth sampling, correction steps,
motion commands, TTS text, waypoint targets, arm speeds, gripper targets, or EE
offset sizes.

If V4 is not suitable onsite, run V1 or V3 directly:

    ./run_fast_live_script.sh yolo/task_all_pick_place_ab.py --execute
    ./run_fast_live_script.sh yolo/task_all_pick_place_ab_v3.py --execute
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
    namespace: dict[str, Any] = runpy.run_path(str(script_path), run_name=f"_wxf_v4_{script_path.stem}")
    sequence = namespace.get("TASK_SEQUENCE")
    if not isinstance(sequence, list) or not all(isinstance(item, str) for item in sequence):
        raise RuntimeError(f"{script_path.name} does not expose a valid TASK_SEQUENCE")
    return list(sequence)


def _restore_environment(snapshot: dict[str, str]) -> None:
    os.environ.clear()
    os.environ.update(snapshot)


def _apply_v4_profile() -> dict[str, str]:
    """Apply V4 software-only profile and return values for log visibility."""
    profile = {
        "G2_WXF_TTS_PRE_PLAY_DELAY_S": os.environ.get("G2_WXF_V4_TTS_PRE_PLAY_DELAY_S", "0.3"),
        "G2_WXF_NAV_IDLE_STABLE_S": os.environ.get("G2_WXF_V4_NAV_IDLE_STABLE_S", "0.5"),
        "G2_WXF_NAV_SKIP_PRE_IDLE_FIRST": os.environ.get("G2_WXF_V4_NAV_SKIP_PRE_IDLE_FIRST", "1"),
        "G2_WXF_NAV_CANCEL_EXISTING_FIRST": os.environ.get("G2_WXF_V4_NAV_CANCEL_EXISTING_FIRST", "0"),
        "G2_WXF_NAV_IDLE_WAIT_TIMEOUT_S": os.environ.get("G2_WXF_V4_NAV_IDLE_WAIT_TIMEOUT_S", "120.0"),
        "G2_WXF_YOLO_RESIDENT": os.environ.get("G2_WXF_V4_YOLO_RESIDENT", "1"),
    }
    os.environ.update(profile)
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V4 low-risk MQTT runner for pick A, place A, pick B, and place B"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="execute the full live MQTT sequence; default prints the plan only",
    )
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    profile = _apply_v4_profile()
    print("# yolo/task_all_pick_place_ab_v4.py")
    print(f"# children={len(CHILDREN)}, mode={'execute' if args.execute else 'dry-run plan'}")
    print("# baseline_v1=yolo/task_all_pick_place_ab.py")
    print("# optimization=V3 profile + resident yolo_depth.py model cache")
    for key, value in profile.items():
        print(f"# v4_profile: {key}={value}")

    overall_started_at = time.time()
    for child_index, (label, filename, sequence_name) in enumerate(CHILDREN, 1):
        child_path = base / filename
        if not child_path.exists():
            print(f"missing child script: {child_path}")
            return 1

        env_before_child = dict(os.environ)
        child_started_at = time.time()
        try:
            sequence = _load_child_sequence(child_path)
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
    print(f"# v4_total_timing: status=done duration_s={total_duration_s:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
