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


TASK_SEQUENCE = ['python ../BOX_528_1/move-gopullcar.py', 'python move_whole_body_by_json.py ../positions/car_grab_5.json', 'python move_whole_body_by_json.py ../positions/car_grab_4.json', 'python offset_move_car_grab.py', 'python ../BOX_528_1/move-pullcar.py', 'python move_whole_body_by_json.py ../positions/car_grab_4.json', 'python move_whole_body_by_json.py ../positions/car_grab_5.json']


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Migrated safe sequence wrapper for yolo/task_all_pull_car.py")
    parser.add_argument("--execute", action="store_true", help="execute only migrated scripts inside this workspace; default prints plan")
    args = parser.parse_args()
    return run_sequence("yolo/task_all_pull_car.py", TASK_SEQUENCE, Path(__file__).resolve().parent, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
