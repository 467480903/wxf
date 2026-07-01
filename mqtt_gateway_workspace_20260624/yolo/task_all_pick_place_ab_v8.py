#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V8 idle-first continuous A/B pick-place runner.

V8 keeps V7's child order, task order, safety boundaries, waypoint targets,
arm speeds, gripper targets, EE offset sizes, camera captures, YOLO detections,
depth sampling, correction steps, and TTS behavior.

The only V8 behavior change is the navigation profile: V8 does not skip the
pre-idle wait before the first waypoint inside each navigation child wrapper.
This should avoid the transient pnc_task_state_not_idle failed task records
seen in V7, while retaining V7's wait-idle-before-busy-retry fallback.

If V8 is not suitable onsite, run the already validated V7 directly:

    ./run_fast_live_script.sh yolo/task_all_pick_place_ab_v7.py --execute
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
    namespace: dict[str, Any] = runpy.run_path(str(script_path), run_name=f"_wxf_v8_{script_path.stem}")
    sequence = namespace.get("TASK_SEQUENCE")
    if not isinstance(sequence, list) or not all(isinstance(item, str) for item in sequence):
        raise RuntimeError(f"{script_path.name} does not expose a valid TASK_SEQUENCE")
    return list(sequence)


def _restore_environment(snapshot: dict[str, str]) -> None:
    os.environ.clear()
    os.environ.update(snapshot)


def _apply_v8_profile() -> dict[str, str]:
    """Apply V8 idle-first continuity profile and return values for log visibility."""
    profile = {
        "G2_WXF_TTS_PRE_PLAY_DELAY_S": os.environ.get("G2_WXF_V8_TTS_PRE_PLAY_DELAY_S", "0.0"),
        "G2_WXF_NAV_IDLE_STABLE_S": os.environ.get("G2_WXF_V8_NAV_IDLE_STABLE_S", "0.15"),
        "G2_WXF_NAV_IDLE_WAIT_POLL_S": os.environ.get("G2_WXF_V8_NAV_IDLE_WAIT_POLL_S", "0.15"),
        "G2_WXF_NAV_BUSY_WAIT_IDLE_BEFORE_RETRY": os.environ.get("G2_WXF_V8_NAV_BUSY_WAIT_IDLE_BEFORE_RETRY", "1"),
        "G2_WXF_NAV_SKIP_PRE_IDLE_FIRST": os.environ.get("G2_WXF_V8_NAV_SKIP_PRE_IDLE_FIRST", "0"),
        "G2_WXF_NAV_CANCEL_EXISTING_FIRST": os.environ.get("G2_WXF_V8_NAV_CANCEL_EXISTING_FIRST", "1"),
        "G2_WXF_NAV_IDLE_WAIT_TIMEOUT_S": os.environ.get("G2_WXF_V8_NAV_IDLE_WAIT_TIMEOUT_S", "120.0"),
        "G2_WXF_NAV_BUSY_RETRY_DELAY_S": os.environ.get("G2_WXF_V8_NAV_BUSY_RETRY_DELAY_S", "0.10"),
        "G2_WXF_NAV_POLL_INTERVAL_S": os.environ.get("G2_WXF_V8_NAV_POLL_INTERVAL_S", "0.15"),
        "G2_WXF_FAST_WHOLE_BODY_SPLIT_DELAY_S": os.environ.get("G2_WXF_V8_FAST_WHOLE_BODY_SPLIT_DELAY_S", "0.02"),
        "G2_WXF_YOLO_RESIDENT": os.environ.get("G2_WXF_V8_YOLO_RESIDENT", "1"),
        "G2_WXF_MP3_INLINE": os.environ.get("G2_WXF_V8_MP3_INLINE", "1"),
    }
    os.environ.update(profile)
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V8 idle-first MQTT runner for pick A, place A, pick B, and place B"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="execute the full live MQTT sequence; default prints the plan only",
    )
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    profile = _apply_v8_profile()
    print("# yolo/task_all_pick_place_ab_v8.py")
    print(f"# children={len(CHILDREN)}, mode={'execute' if args.execute else 'dry-run plan'}")
    print("# baseline_v7=yolo/task_all_pick_place_ab_v7.py")
    print("# optimization=V7 profile + idle-first navigation submission")
    for key, value in profile.items():
        print(f"# v8_profile: {key}={value}")

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
            # Some child scripts set pacing defaults while exposing TASK_SEQUENCE.
            # Re-apply the isolated V8 profile after loading those scripts.
            _apply_v8_profile()
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
    print(f"# v8_total_timing: status=done duration_s={total_duration_s:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
