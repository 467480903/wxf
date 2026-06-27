#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V3 balanced-speed continuous A/B pick-place runner.

V1 remains the proven baseline:

    yolo/task_all_pick_place_ab.py

V2 removes one orchestration layer but keeps conservative runtime waits.
V3 keeps V2's single-process orchestration and adds only software-wait tuning:

- TTS still plays, but the pre-play delay is reduced from 1.0s to 0.3s.
- PNC idle stability wait is reduced from 1.0s to 0.5s.

This file does not change the four validated child task scripts, motion step
order, waypoint targets, arm velocities, gripper targets, EE offset sizes, camera
steps, or YOLO model calls. If V3 is not suitable onsite, run V1 directly.
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
    namespace: dict[str, Any] = runpy.run_path(str(script_path), run_name=f"_wxf_v3_{script_path.stem}")
    sequence = namespace.get("TASK_SEQUENCE")
    if not isinstance(sequence, list) or not all(isinstance(item, str) for item in sequence):
        raise RuntimeError(f"{script_path.name} does not expose a valid TASK_SEQUENCE")
    return list(sequence)


def _restore_environment(snapshot: dict[str, str]) -> None:
    os.environ.clear()
    os.environ.update(snapshot)


def _apply_v3_profile() -> dict[str, str]:
    """Apply V3 software-wait profile and return the values for logging."""
    profile = {
        "G2_WXF_TTS_PRE_PLAY_DELAY_S": os.environ.get("G2_WXF_V3_TTS_PRE_PLAY_DELAY_S", "0.3"),
        "G2_WXF_NAV_IDLE_STABLE_S": os.environ.get("G2_WXF_V3_NAV_IDLE_STABLE_S", "0.5"),
    }
    os.environ.update(profile)
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V3 balanced-speed MQTT runner for pick A, place A, pick B, and place B"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="execute the full live MQTT sequence; default prints the plan only",
    )
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    profile = _apply_v3_profile()
    print("# yolo/task_all_pick_place_ab_v3.py")
    print(f"# children={len(CHILDREN)}, mode={'execute' if args.execute else 'dry-run plan'}")
    print("# baseline_v1=yolo/task_all_pick_place_ab.py")
    print("# optimization=V2 single-process orchestration + conservative software-wait tuning")
    for key, value in profile.items():
        print(f"# v3_profile: {key}={value}")

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
    print(f"# v3_total_timing: status=done duration_s={total_duration_s:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
