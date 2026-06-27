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


# Source of truth: /data/wxf/wxf/yolo/task_all.py on 192.168.0.6.
TASK_SEQUENCE = [
    "python ../interaction/play_tts_cli.py 任务开始,将运动到A件小车处,抓取工件,mission start,moving to picking up place for product A,",
    "python ../BOX_528_1/move-ready1.py",
    "python ../Robot/move_ee_pose_open_2.py",
    "python ../BOX_528_1/move_arm_by_json_grab_delever.py",
    "python ../BOX_528_1/move-pick1.py",
    "python cam_get_head.py",
    "yolo-env/bin/python yolo_depth.py holes.pt 1",
    "python correct_waist.py",
    "python cam_get_head.py",
    "yolo-env/bin/python yolo_depth.py holes.pt 1",
    "python ../BOX_528_1/move_arm_by_json_grab_1st.py",
    "python ../BOX_528_1/offset_move_push_grab.py",
    "python ../interaction/play_tts_cli.py 抓取工件",
    "python ../Robot/move_ee_pose_close_2.py",
    "python ../BOX_528_1/offset_move_up.py",
    "python ../BOX_528_1/offset_move_pull.py",
    "python ../BOX_528_1/move-adjust1.py",
    "python ../interaction/play_tts_cli.py 将运行到A件的放置位",
    "python ../BOX_528_1/move_arm_by_json_grab_delever.py",
    "python ../BOX_528_1/move-put1.py",
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Fast MQTT/Gateway sequence wrapper for yolo/task_all.py")
    parser.add_argument("--execute", action="store_true", help="execute the MQTT fast sequence; default prints plan")
    args = parser.parse_args()
    return run_sequence("yolo/task_all.py", TASK_SEQUENCE, Path(__file__).resolve().parent, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
