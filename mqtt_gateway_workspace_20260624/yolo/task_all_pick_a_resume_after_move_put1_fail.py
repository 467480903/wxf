#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    _common = _parent / "mqtt_common"
    if _common.is_dir():
        sys.path.insert(0, str(_common))
        break

from mqtt_common import run_sequence


# Resume only after task_all_pick_a.py has already completed the pick/pull path
# and failed at step 18 inside BOX_528_1/move-put1.py. Do not use this as a
# replacement for a fresh full A-pick run.
TASK_SEQUENCE = [
    "python ../BOX_528_1/move-put1.py",
    "python ../BOX_528_1/move_arm_by_json_grab_delever.py",
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Resume task_all_pick_a.py after step 18 move-put1 failure")
    parser.add_argument("--execute", action="store_true", help="execute the MQTT fast sequence; default prints plan")
    args = parser.parse_args()
    return run_sequence(
        "yolo/task_all_pick_a_resume_after_move_put1_fail.py",
        TASK_SEQUENCE,
        Path(__file__).resolve().parent,
        execute=args.execute,
    )


if __name__ == "__main__":
    raise SystemExit(main())
