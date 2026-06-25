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


TASK_SEQUENCE = ['python move_whole_body_by_json.py ../positions/pick_standby.json', 'python cam_get_head.py', 'yolo-env/bin/python yolo_depth.py place_product.pt 10', 'cp yolo_depth_result.json yolo_depth_result_2.json', 'python correct_waist.py', 'python cam_get_head.py', 'yolo-env/bin/python yolo_depth.py place_product.pt 10', 'cp yolo_depth_result.json yolo_depth_result_3.json', 'python move_ee_pose_right_half.py', 'python move_whole_body_by_json.py ../positions/place_b_1.json', 'python move_whole_body_by_json.py ../positions/place_b_2.json', 'python move_whole_body_by_json.py ../positions/place_b_3.json', 'mv yolo_depth_result_2.json yolo_depth_result.json', 'python correct_waist.py', 'python move_arm_by_json.py ../positions/place_b_4.json', 'python offset_move_left_025.py', 'mv yolo_depth_result_3.json yolo_depth_result.json', 'python offset_move_horizon.py', 'python offset_move_vertical.py', 'python offset_move_downward_002.py', 'python offset_move_downward_002.py', 'python move_ee_pose_open_05.py', 'python offset_move_downward_002.py', 'python offset_move_downward_002.py', 'python offset_move_downward_002.py', 'python offset_move_downward_002.py', 'python ../Robot/move_ee_pose_open_2.py', 'python offset_move_pull_back.py', 'python move_whole_body_by_json.py ../positions/pick_standby.json']


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Migrated safe sequence wrapper for yolo/task_all_place_b.py")
    parser.add_argument("--execute", action="store_true", help="execute only migrated scripts inside this workspace; default prints plan")
    args = parser.parse_args()
    return run_sequence("yolo/task_all_place_b.py", TASK_SEQUENCE, Path(__file__).resolve().parent, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
