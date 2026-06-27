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


# Source of truth: /data/wxf/wxf/yolo/task_all.py.
# Keep this sequence order identical to the original script; only the execution
# layer is converted to the MQTT/Gateway wrappers.
TASK_SEQUENCE = [
    "python ../BOX_528_1/move-ready1.py",
    "python ../Robot/move_ee_pose_open_2.py",
    "python ../BOX_528_1/move_arm_by_json_grab_delever.py",
    "python ../BOX_528_1/move-pick1.py",
    "python ../interaction/play_tts_cli.py 大家好，我将进行焊装工位的上件和更换台车演示，我将识别工件A的位置并调整，然后取出一枚工件A。",
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
    "python ../BOX_528_1/move-put1.py"
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Fast MQTT/Gateway sequence wrapper for yolo/task_all.py")
    parser.add_argument("--execute", action="store_true", help="execute the MQTT fast sequence; default prints plan")
    args = parser.parse_args()
    return run_sequence("yolo/task_all.py", TASK_SEQUENCE, Path(__file__).resolve().parent, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
