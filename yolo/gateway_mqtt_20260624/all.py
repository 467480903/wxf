#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from gateway_sequence_runner import parse_sequence_args, run_sequence


TASK_SEQUENCE = [
    "python move_whole_body_by_json.py ../posoitions/p1.json",
    "python move_whole_body_by_json.py ../posoitions/arm_position_to_grab_2.json",
    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",
    "python offset_move_left_002.py",
    "python offset_move_left_002.py",
    "python move_ee_pose_open_05.py",
    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",
    "python ../Robot/move_ee_pose_open_2.py",
    "python offset_move_pull_back.py",
    "python offset_move_down.py",
    "python move_whole_body_by_json.py ../posoitions/pick_standby.json",
]


def main() -> int:
    args = parse_sequence_args("migrated all.py sequence")
    return run_sequence("all.py", TASK_SEQUENCE, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
