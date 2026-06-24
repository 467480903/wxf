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


TASK_SEQUENCE = ['python ../BOX_528_1/move-ready1.py', 'python ../Robot/move_ee_pose_open_2.py', 'python ../BOX_528_1/move_arm_by_json_grab_delever.py', 'python ../BOX_528_1/move-pick1.py', 'python ../BOX_528_1/move_arm_by_json_grab_1st.py', 'python ../BOX_528_1/offset_move_push_grab.py', 'python ../Robot/move_ee_pose_close_2.py', 'python ../BOX_528_1/offset_move_up.py', 'python ../BOX_528_1/offset_move_pull.py', 'python ../BOX_528_1/move-adjust1.py', 'python ../BOX_528_1/move_arm_by_json_grab_delever.py', 'python ../BOX_528_1/move-put1.py', 'python move_whole_body_by_json.py ../positions/pick_standby.json', 'python cam_get_head.py', 'yolo-env/bin/python yolo_depth.py place_product.pt 2', 'python correct_waist.py', 'python cam_get_head.py', 'yolo-env/bin/python yolo_depth.py place_product.pt 2', 'python move_ee_pose_right_half.py', 'python move_arm_by_json.py ../positions/place_1.json', 'python move_arm_by_json.py ../positions/place_2.json', 'python offset_move_horizon.py', 'python offset_move_downward_004.py', 'python move_ee_pose_open_05.py', 'python offset_move_downward_002.py', 'python offset_move_forward_001.py', 'python offset_move_downward_004.py', 'python offset_move_downward_004.py', 'python ../Robot/move_ee_pose_open_2.py', 'python offset_move_pull_back.py', 'python move_whole_body_by_json.py ../positions/pick_standby.json']


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Migrated safe sequence wrapper for yolo/task_all.py")
    parser.add_argument("--execute", action="store_true", help="execute only migrated scripts inside this workspace; default prints plan")
    args = parser.parse_args()
    return run_sequence("yolo/task_all.py", TASK_SEQUENCE, Path(__file__).resolve().parent, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
