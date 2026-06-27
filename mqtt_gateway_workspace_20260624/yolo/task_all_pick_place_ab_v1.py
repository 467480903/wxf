#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the validated A/B pick-place demo as one continuous MQTT sequence.

This wrapper intentionally does not duplicate the detailed motion steps from
the four existing task scripts. Those scripts are already validated one by one,
so this file only chains their public entry points in the same order David has
been running manually:

1. task_all_pick_a.py
2. task_all_place_a.py
3. task_all_pick_b.py
4. task_all_place_b.py

Keeping the four child scripts as the source of truth avoids drift: fixes to an
individual pick/place flow are automatically used by the combined flow.

Continuity/speed/stability constraints:

- Do not add sleeps between the four child scripts unless the onsite operator
  explicitly asks for a new pause. The launcher should start the next child as
  soon as the previous one exits successfully.
- Do not inline or rewrite the child task sequences here. The individual
  scripts are the validated units, and this wrapper is only orchestration.
- Do not add HTTP task submission here. Motion must continue through the MQTT
  service path; HTTP is only for video/UI service usage.
- If a child exits non-zero, stop immediately and preserve the failing child
  log. Continuing after a failed pick/place step is less stable than failing
  fast and letting the operator inspect the robot state.
"""

from __future__ import annotations

import sys
from pathlib import Path


for _parent in Path(__file__).resolve().parents:
    _common = _parent / "mqtt_common"
    if _common.is_dir():
        sys.path.insert(0, str(_common))
        break

from mqtt_common import run_sequence


# Do not change the individual task scripts here. This sequence is only the
# top-level orchestration layer that replaces four manual shell invocations.
# mqtt_common.run_sequence executes these entries as local child Python
# processes and starts the next entry immediately after the previous one returns
# 0, so the continuous flow preserves the same pacing as David's manual order.
TASK_SEQUENCE = [
    "python task_all_pick_a.py --execute",
    "python task_all_place_a.py --execute",
    "python task_all_pick_b.py --execute",
    "python task_all_place_b.py --execute",
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run pick A, place A, pick B, and place B as one continuous MQTT flow"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="execute the full live MQTT sequence; default prints the plan only",
    )
    args = parser.parse_args()
    return run_sequence(
        "yolo/task_all_pick_place_ab.py",
        TASK_SEQUENCE,
        Path(__file__).resolve().parent,
        execute=args.execute,
    )


if __name__ == "__main__":
    raise SystemExit(main())
