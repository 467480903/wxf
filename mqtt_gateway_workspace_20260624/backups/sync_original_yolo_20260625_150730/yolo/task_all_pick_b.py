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


TASK_SEQUENCE = ['python ../BOX_528_1/move-pick2.py', 'python move_whole_body_by_json.py ../positions/pick_b_watch.json', 'python move_whole_body_by_json.py ../positions/pick_b_1.json', 'python move_arm_by_json.py ../positions/pick_b_2.json', 'python ../Robot/move_ee_pose_close_2.py', 'python offset_move_upward_015.py', 'python offset_move_pull_back.py', 'python ../BOX_528_1/move-adjust2.py', 'python move_whole_body_by_json.py ../positions/pick_standby.json', 'python ../BOX_528_1/move-put2.py']


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Migrated safe sequence wrapper for yolo/task_all_pick_b.py")
    parser.add_argument("--execute", action="store_true", help="execute only migrated scripts inside this workspace; default prints plan")
    args = parser.parse_args()
    return run_sequence("yolo/task_all_pick_b.py", TASK_SEQUENCE, Path(__file__).resolve().parent, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
