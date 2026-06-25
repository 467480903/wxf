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


# Source of truth: /data/wxf/wxf/yolo/task_all_pick_b.py on 192.168.0.6.
TASK_SEQUENCE = [
    "python ../interaction/play_tts_cli.py 将执行B件的抓取",
    "python ../BOX_528_1/move-pick2.py",
    "python cam_get_head.py",
    "yolo-env/bin/python yolo_depth.py holes.pt 1",
    "python correct_waist.py",
    "python cam_get_head.py",
    "yolo-env/bin/python yolo_depth.py holes.pt 1",
    "python ../BOX_528_1/move_arm_by_json_grab_1st.py",
    "python ../BOX_528_1/offset_move_downpickb.py",
    "python ../BOX_528_1/offset_move_push_grab.py",
    "python ../interaction/play_tts_cli.py 抓取工件",
    "python ../Robot/move_ee_pose_close_2.py",
    "python ../BOX_528_1/offset_move_up.py",
    "python ../BOX_528_1/offset_move_pull.py",
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Fast MQTT/Gateway sequence wrapper for yolo/task_all_pick_b.py")
    parser.add_argument("--execute", action="store_true", help="execute the MQTT fast sequence; default prints plan")
    args = parser.parse_args()
    return run_sequence("yolo/task_all_pick_b.py", TASK_SEQUENCE, Path(__file__).resolve().parent, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
