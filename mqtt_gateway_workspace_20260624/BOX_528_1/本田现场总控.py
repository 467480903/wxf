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


TASK_SEQUENCE = ['move-ready1.py', 'move_ee_pose_open_2.py', 'move_arm_by_json_grab_above_第一根.py', 'move-pick1.py', 'move_ee_pose_close_2.py', 'offset_move_up.py', 'move-adjust1.py', 'move_arm_by_json_grab_above_2.py', 'move-put1.py', 'offset_move_down.py', 'move_ee_pose_open_2.py', 'offset_move_pull.py', 'move-back.py']


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Migrated safe sequence wrapper for BOX_528_1/本田现场总控.py")
    parser.add_argument("--execute", action="store_true", help="execute only migrated scripts inside this workspace; default prints plan")
    args = parser.parse_args()
    return run_sequence("BOX_528_1/本田现场总控.py", TASK_SEQUENCE, Path(__file__).resolve().parent, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
