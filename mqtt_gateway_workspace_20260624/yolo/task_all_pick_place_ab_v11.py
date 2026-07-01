#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V11 cycle-time runner for G2A A/B pick-place.

V11 keeps V10's conservative vision, audio, and navigation behavior, then adds
state-confirmed whole-body no-op skipping.

Before a `move_whole_body_by_json.py` command, mqtt_common can read the current
GDK joint state and skip the command only when all target head/waist/arm joints
are already within a tight tolerance. If the state is missing or outside
tolerance, the original command still runs.

No visual thresholds are relaxed here. `maybe_refresh_yolo_depth.py` still
reuses a second-pass result only when the first-pass YOLO/depth result is stable.
Audio/MP3 prompts are also kept enabled.
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

from mqtt_common import env_flag, run_sequence


CHILDREN = [
    ("pick_a", "task_all_pick_a.py", "yolo/task_all_pick_a.py"),
    ("place_a", "task_all_place_a.py", "yolo/task_all_place_a.py"),
    ("pick_b", "task_all_pick_b.py", "yolo/task_all_pick_b.py"),
    ("place_b", "task_all_place_b.py", "yolo/task_all_place_b.py"),
]


REDUNDANT_PLACE_B_STANDBY = "python move_whole_body_by_json.py ../positions/pick_standby.json"


def _load_child_sequence(script_path: Path) -> list[str]:
    namespace: dict[str, Any] = runpy.run_path(str(script_path), run_name=f"_wxf_v11_{script_path.stem}")
    sequence = namespace.get("TASK_SEQUENCE")
    if not isinstance(sequence, list) or not all(isinstance(item, str) for item in sequence):
        raise RuntimeError(f"{script_path.name} does not expose a valid TASK_SEQUENCE")
    return list(sequence)


def _restore_environment(snapshot: dict[str, str]) -> None:
    os.environ.clear()
    os.environ.update(snapshot)


def _v11_env(name: str, default: str) -> str:
    return os.environ.get(
        f"G2_WXF_V11_{name}",
        os.environ.get(
            f"G2_WXF_V10_{name}",
            os.environ.get(f"G2_WXF_V9_{name}", os.environ.get(f"G2_WXF_V8_{name}", default)),
        ),
    )


def _apply_v11_profile() -> dict[str, str]:
    """Apply V11 continuity, vision, audio, and no-op settings."""
    profile = {
        "G2_WXF_TTS_PRE_PLAY_DELAY_S": _v11_env("TTS_PRE_PLAY_DELAY_S", "0.0"),
        "G2_WXF_NAV_IDLE_STABLE_S": _v11_env("NAV_IDLE_STABLE_S", "0.0"),
        "G2_WXF_NAV_IDLE_WAIT_POLL_S": _v11_env("NAV_IDLE_WAIT_POLL_S", "0.10"),
        "G2_WXF_NAV_BUSY_WAIT_IDLE_BEFORE_RETRY": _v11_env("NAV_BUSY_WAIT_IDLE_BEFORE_RETRY", "1"),
        "G2_WXF_NAV_SKIP_PRE_IDLE_FIRST": _v11_env("NAV_SKIP_PRE_IDLE_FIRST", "0"),
        "G2_WXF_NAV_CANCEL_EXISTING_FIRST": _v11_env("NAV_CANCEL_EXISTING_FIRST", "1"),
        "G2_WXF_NAV_IDLE_WAIT_TIMEOUT_S": _v11_env("NAV_IDLE_WAIT_TIMEOUT_S", "120.0"),
        "G2_WXF_NAV_BUSY_RETRY_DELAY_S": _v11_env("NAV_BUSY_RETRY_DELAY_S", "0.05"),
        "G2_WXF_NAV_POLL_INTERVAL_S": _v11_env("NAV_POLL_INTERVAL_S", "0.15"),
        "G2_WXF_FAST_WHOLE_BODY_SPLIT_DELAY_S": _v11_env("FAST_WHOLE_BODY_SPLIT_DELAY_S", "0.02"),
        "G2_WXF_YOLO_RESIDENT": _v11_env("YOLO_RESIDENT", "1"),
        "G2_WXF_MP3_INLINE": _v11_env("MP3_INLINE", "1"),
        "G2_WXF_VISION_SECOND_PASS_REUSE": _v11_env("VISION_SECOND_PASS_REUSE", "1"),
        "G2_WXF_VISION_REUSE_MAX_HORIZONTAL_PX": _v11_env("VISION_REUSE_MAX_HORIZONTAL_PX", "2.0"),
        "G2_WXF_VISION_REUSE_MAX_SLOPE_DEG": _v11_env("VISION_REUSE_MAX_SLOPE_DEG", "0.5"),
        "G2_WXF_VISION_REUSE_MAX_DEPTH_DIFF_MM": _v11_env("VISION_REUSE_MAX_DEPTH_DIFF_MM", "60.0"),
        "G2_WXF_V10_SKIP_REDUNDANT_PLACE_B_STANDBY": _v11_env("SKIP_REDUNDANT_PLACE_B_STANDBY", "1"),
        "G2_WXF_WHOLE_BODY_NOOP_SKIP": _v11_env("WHOLE_BODY_NOOP_SKIP", "1"),
        "G2_WXF_WHOLE_BODY_NOOP_TOL_RAD": _v11_env("WHOLE_BODY_NOOP_TOL_RAD", "0.01"),
        "G2_WXF_WHOLE_BODY_NOOP_LOG_MISS": _v11_env("WHOLE_BODY_NOOP_LOG_MISS", "0"),
    }
    os.environ.update(profile)
    return profile


def _optimize_child_sequence(label: str, sequence: list[str]) -> list[str]:
    optimized = list(sequence)
    if label != "place_b":
        return optimized
    if not env_flag("G2_WXF_V10_SKIP_REDUNDANT_PLACE_B_STANDBY", True):
        return optimized
    if len(optimized) >= 2 and optimized[1] == REDUNDANT_PLACE_B_STANDBY:
        removed = optimized.pop(1)
        print(
            "# v11_sequence_optimization: label=place_b removed_step=02 "
            f"entry={removed!r} reason=pick_b_already_ended_at_pick_standby",
            flush=True,
        )
    else:
        print(
            "# v11_sequence_optimization_skipped: label=place_b "
            "reason=expected_redundant_standby_not_found",
            flush=True,
        )
    return optimized


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V11 cycle-time MQTT runner for pick A, place A, pick B, and place B"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="execute the full live MQTT sequence; default prints the plan only",
    )
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    profile = _apply_v11_profile()
    print("# yolo/task_all_pick_place_ab_v11.py")
    print(f"# children={len(CHILDREN)}, mode={'execute' if args.execute else 'dry-run plan'}")
    print("# baseline_v10=yolo/task_all_pick_place_ab_v10.py")
    print("# optimization=V10 + state-confirmed whole-body no-op skip")
    for key, value in profile.items():
        print(f"# v11_profile: {key}={value}")

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
            _apply_v11_profile()
            sequence = _optimize_child_sequence(label, sequence)
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
    print(f"# v11_total_timing: status=done duration_s={total_duration_s:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
