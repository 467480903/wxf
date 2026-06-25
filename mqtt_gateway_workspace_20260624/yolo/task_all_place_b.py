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


# Source of truth: /data/wxf/wxf/yolo/task_all_place_b.py on G2A (10.185.207.186), synced 2026-06-25.
TASK_SEQUENCE = [
    'python ../Robot/move_ee_pose_close_2.py',
    'python move_whole_body_by_json.py ../positions/pick_standby.json',
    'python ../interaction/play_tts_cli.py 执行基于视觉模型的推理,通过识别两个销子,然后计算销子的中点,和销子的深度值,来计算机器人的腰部旋转值,和纵声偏移量,和水平偏移量',
    'python cam_get_head.py',
    'yolo-env/bin/python cam_get_head_send.py shelf.pt 1',
    'cp yolo_depth_result.json yolo_depth_result_2.json',
    'python correct_waist.py',
    'python cam_get_head.py',
    'yolo-env/bin/python cam_get_head_send.py shelf.pt 1',
    'cp yolo_depth_result.json yolo_depth_result_3.json',
    'python move_ee_pose_right_half.py',
    'python move_whole_body_by_json.py ../positions/place_b_2.json',
    'python move_whole_body_by_json.py ../positions/place_b_3.json',
    'mv yolo_depth_result_2.json yolo_depth_result.json',
    'python correct_waist.py',
    'python move_arm_by_json.py ../positions/place_b_4.json',
    'python offset_move_left_002.py',
    'python move_arm_by_json.py ../positions/place_b_5.json',
    'mv yolo_depth_result_3.json yolo_depth_result.json',
    'python offset_move_horizon_b.py',
    'python offset_move_vertical_b.py',
    'python offset_move_downward_002.py',
    'python offset_move_downward_002.py',
    'python move_ee_pose_open_05.py',
    'python offset_move_downward_002.py',
    'python offset_move_downward_002.py',
    'python ../Robot/move_ee_pose_open_2.py',
    'python offset_move_pull_back.py',
    'python move_whole_body_by_json.py ../positions/pick_standby.json',
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Fast MQTT/Gateway sequence wrapper for yolo/task_all_place_b.py")
    parser.add_argument("--execute", action="store_true", help="execute the MQTT fast sequence; default prints plan")
    args = parser.parse_args()
    return run_sequence("yolo/task_all_place_b.py", TASK_SEQUENCE, Path(__file__).resolve().parent, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
