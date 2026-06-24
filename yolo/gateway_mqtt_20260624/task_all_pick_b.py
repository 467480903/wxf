#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from gateway_sequence_runner import parse_sequence_args, run_sequence


TASK_SEQUENCE = [
    "python ../BOX_528_1/move-pick2.py",
    "python move_whole_body_by_json.py ../positions/pick_b_watch.json",
    "python move_whole_body_by_json.py ../positions/pick_b_1.json",
    "python move_arm_by_json.py ../positions/pick_b_2.json",
    "python ../Robot/move_ee_pose_close_2.py",
    "python offset_move_upward_015.py",
    "python offset_move_pull_back.py",
    "python ../BOX_528_1/move-adjust2.py",
    "python move_whole_body_by_json.py ../positions/pick_standby.json",
    "python ../BOX_528_1/move-put2.py",
]


def main() -> int:
    args = parse_sequence_args("migrated task_all_pick_b.py sequence")
    return run_sequence("task_all_pick_b.py", TASK_SEQUENCE, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
