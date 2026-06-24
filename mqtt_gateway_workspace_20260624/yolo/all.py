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


TASK_SEQUENCE = ['python move_whole_body_by_json.py ../posoitions/p1.json', 'python move_whole_body_by_json.py ../posoitions/arm_position_to_grab_2.json', 'python offset_move_downward_002.py', 'python offset_move_downward_002.py', 'python offset_move_left_002.py', 'python offset_move_left_002.py', 'python move_ee_pose_open_05.py', 'python offset_move_downward_002.py', 'python offset_move_downward_002.py', 'python offset_move_downward_002.py', 'python offset_move_downward_002.py', 'python offset_move_downward_002.py', 'python ../Robot/move_ee_pose_open_2.py', 'python offset_move_pull_back.py', 'python offset_move_down.py', 'python move_whole_body_by_json.py ../posoitions/pick_standby.json']


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Migrated safe sequence wrapper for yolo/all.py")
    parser.add_argument("--execute", action="store_true", help="execute only migrated scripts inside this workspace; default prints plan")
    args = parser.parse_args()
    return run_sequence("yolo/all.py", TASK_SEQUENCE, Path(__file__).resolve().parent, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
