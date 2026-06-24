#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from gateway_sequence_runner import parse_sequence_args, run_sequence


TASK_SEQUENCE = [
    "python move_whole_body_by_json.py ../positions/pick_standby.json",
    "python cam_get_head.py",
    "yolo-env/bin/python yolo_depth.py place_product.pt 10",
    "cp yolo_depth_result.json yolo_depth_result_2.json",
    "python correct_waist.py",
    "python cam_get_head.py",
    "yolo-env/bin/python yolo_depth.py place_product.pt 10",
    "cp yolo_depth_result.json yolo_depth_result_3.json",
    "python move_ee_pose_right_half.py",
    "python move_whole_body_by_json.py ../positions/place_b_1.json",
    "python move_whole_body_by_json.py ../positions/place_b_2.json",
    "python move_whole_body_by_json.py ../positions/place_b_3.json",
    "mv yolo_depth_result_2.json yolo_depth_result.json",
    "python correct_waist.py",
    "python move_arm_by_json.py ../positions/place_b_4.json",
    "python offset_move_left_025.py",
    "mv yolo_depth_result_3.json yolo_depth_result.json",
    "python offset_move_horizon.py",
    "python offset_move_vertical.py",
    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",
    "python move_ee_pose_open_05.py",
    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",
    "python ../Robot/move_ee_pose_open_2.py",
    "python offset_move_pull_back.py",
    "python move_whole_body_by_json.py ../positions/pick_standby.json",
]


def main() -> int:
    args = parse_sequence_args("migrated task_all_place_b.py sequence")
    return run_sequence("task_all_place_b.py", TASK_SEQUENCE, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
