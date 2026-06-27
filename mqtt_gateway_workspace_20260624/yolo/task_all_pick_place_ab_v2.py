#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V2 continuous A/B pick-place runner.

V1, the proven baseline, remains:

    yolo/task_all_pick_place_ab.py

V2 keeps the same four validated child task scripts as the source of truth, but
removes one layer of child Python process execution. Instead of running:

    python task_all_pick_a.py --execute
    python task_all_place_a.py --execute
    python task_all_pick_b.py --execute
    python task_all_place_b.py --execute

it loads each child script's TASK_SEQUENCE and calls mqtt_common.run_sequence
directly in this process.

The important safety/stability boundary is preserved:

- The original child files are not edited.
- Each child still has its own run_sequence call, so vision retry/fallback state
  does not leak between A-pick, A-place, B-pick, and B-place.
- Environment changes made by a child module are restored after that child
  finishes, matching the isolation it had when it ran in its own Python process.
- If any child returns non-zero, V2 stops immediately.
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
    """Load TASK_SEQUENCE from a child script without calling its main()."""
    namespace: dict[str, Any] = runpy.run_path(str(script_path), run_name=f"_wxf_v2_{script_path.stem}")
    sequence = namespace.get("TASK_SEQUENCE")
    if not isinstance(sequence, list) or not all(isinstance(item, str) for item in sequence):
        raise RuntimeError(f"{script_path.name} does not expose a valid TASK_SEQUENCE")
    return list(sequence)


def _restore_environment(snapshot: dict[str, str]) -> None:
    os.environ.clear()
    os.environ.update(snapshot)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V2 continuous MQTT runner for pick A, place A, pick B, and place B"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="execute the full live MQTT sequence; default prints the plan only",
    )
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    print("# yolo/task_all_pick_place_ab_v2.py")
    print(f"# children={len(CHILDREN)}, mode={'execute' if args.execute else 'dry-run plan'}")
    print("# baseline_v1=yolo/task_all_pick_place_ab.py")
    print("# optimization=single-process child orchestration with per-child state isolation")

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
    print(f"# v2_total_timing: status=done duration_s={total_duration_s:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
