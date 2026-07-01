#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import os
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    _common = _parent / "mqtt_common"
    if _common.is_dir():
        sys.path.insert(0, str(_common))
        break

from mqtt_common import run_sequence


# The combined body.move_whole_body_pose path is fastest, but on this onsite
# pack/place-A pose it hit GDK "Broken promise" immediately. Keep the MQTT
# service path and split whole-body JSON into separate Gateway commands.
# Do not skip the head by default: the original task_all_place_a.py executes
# move_whole_body_by_json.py with the full JSON pose, including head joints.
os.environ.setdefault("G2_WXF_FAST_WHOLE_BODY_SPLIT", "1")
os.environ.setdefault("G2_WXF_FAST_WHOLE_BODY_SKIP_HEAD", "0")
os.environ.setdefault("G2_WXF_FAST_WHOLE_BODY_SPLIT_DELAY_S", "0.08")


# Source of truth: /data/wxf/wxf/yolo/task_all_place_a.py on G2A, synced 2026-06-26 17:30 CST.
# Motion entries are executed by mqtt_common.run_sequence as fast_inline MQTT/Gateway
# commands when possible; camera/YOLO/file operations keep the original order.
TASK_SEQUENCE = [
    "python move_whole_body_by_json.py ../positions/pick_standby.json",
    "python mqtt_mp3.py --file JPCH2.mp3",
    "python cam_get_head.py",
    "yolo-env/bin/python yolo_depth.py shelf.pt",
    "python correct_waist.py",
    "python cam_get_head.py",
    "yolo-env/bin/python yolo_depth.py shelf.pt",
    "python move_ee_pose_right_half.py",
    "python move_arm_by_json.py ../positions/place_1.json",
    "python move_arm_by_json.py ../positions/place_2.json",
    "python offset_move_horizon.py",
    "python offset_move_downward_004.py",
    "python move_ee_pose_open_05.py",
    "python offset_move_downward_002.py",
    "python offset_move_forward_001.py",
    "python offset_move_vertical.py",
    "python offset_move_downward_004.py",
    "python offset_move_downward_004.py",
    "python ../Robot/move_ee_pose_open_2.py",
    "python offset_move_pull_back.py",
    "python move_whole_body_by_json.py ../positions/pick_standby.json",
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Fast MQTT/Gateway sequence wrapper for yolo/task_all_place_a.py")
    parser.add_argument("--execute", action="store_true", help="execute the MQTT fast sequence; default prints plan")
    args = parser.parse_args()
    return run_sequence("yolo/task_all_place_a.py", TASK_SEQUENCE, Path(__file__).resolve().parent, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
