#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from gateway_sequence_runner import parse_sequence_args, run_sequence


TASK_SEQUENCE = [
    "python ../BOX_528_1/move-gopullcar.py",
    "python move_whole_body_by_json.py ../positions/car_grab_5.json",
    "python move_whole_body_by_json.py ../positions/car_grab_4.json",
    "python offset_move_car_grab.py",
    "python ../BOX_528_1/move-pullcar.py",
    "python move_whole_body_by_json.py ../positions/car_grab_4.json",
    "python move_whole_body_by_json.py ../positions/car_grab_5.json",
]


def main() -> int:
    args = parse_sequence_args("migrated task_all_pull_car.py sequence")
    return run_sequence("task_all_pull_car.py", TASK_SEQUENCE, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
