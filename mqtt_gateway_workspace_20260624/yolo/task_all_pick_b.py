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


# The final move_whole_body_by_json.py step in the original script runs
# head -> waist -> arms sequentially with 0.2s sleeps between groups.
os.environ["G2_WXF_FAST_WHOLE_BODY_SPLIT_DELAY_S"] = "0.2"

# This pick-B wrapper should preserve the original arm/end-effector motion
# pacing. Earlier demos allow faster non-contact lift/retreat offsets, but this
# flow keeps those offsets at the conservative original step size.
os.environ["G2_WXF_FAST_EE_NONCONTACT_MAX_STEP_M"] = "0.001"
os.environ["G2_WXF_FAST_EE_NONCONTACT_RATE_HZ"] = "50"


# Source of truth: /data/wxf/wxf/yolo/task_all_pick_b.py on G2A.
# Keep the active sequence identical to the original script. Commented-out
# camera/YOLO/TTS/body-pose lines in the original stay omitted here.
# Only the execution layer is converted to the MQTT/Gateway wrappers.
TASK_SEQUENCE = [
    "python ../BOX_528_1/move-pick2.py",
    "python mqtt_mp3.py --file JPCH3.mp3",
    "python ../Robot/move_ee_pose_open_2.py",
    "python ../BOX_528_1/move_arm_by_json_grab_1st.py",
    "python ../BOX_528_1/offset_move_downpickb.py",
    "python ../BOX_528_1/offset_move_push_grab_b.py",
    "python ../Robot/move_ee_pose_close_2.py",
    "python ../BOX_528_1/offset_move_up.py",
    "python ../BOX_528_1/offset_move_pull.py",
    "python ../BOX_528_1/move-adjust2.py",
    "python ../BOX_528_1/move-put2.py",
    "python move_whole_body_by_json.py ../positions/pick_standby.json",
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Fast MQTT/Gateway sequence wrapper for yolo/task_all_pick_b.py")
    parser.add_argument("--execute", action="store_true", help="execute the MQTT fast sequence; default prints plan")
    args = parser.parse_args()
    return run_sequence("yolo/task_all_pick_b.py", TASK_SEQUENCE, Path(__file__).resolve().parent, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
