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


# Resume only after task_all_pick_a.py has already completed steps 1-6 and
# failed at step 7 inside yolo/correct_waist.py. It starts by retrying the
# corrected waist adjustment, then keeps the remaining original A-pick flow.
# Do not use this as a replacement for a fresh full A-pick run if the robot,
# workpiece, or camera result has moved since the failed run.
TASK_SEQUENCE = [
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
    "python ../BOX_528_1/move-put1.py",
    "python ../BOX_528_1/move_arm_by_json_grab_delever.py",
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Resume task_all_pick_a.py after step 7 correct_waist failure")
    parser.add_argument("--execute", action="store_true", help="execute the MQTT fast sequence; default prints plan")
    args = parser.parse_args()
    return run_sequence(
        "yolo/task_all_pick_a_resume_after_correct_waist_fail.py",
        TASK_SEQUENCE,
        Path(__file__).resolve().parent,
        execute=args.execute,
    )


if __name__ == "__main__":
    raise SystemExit(main())
