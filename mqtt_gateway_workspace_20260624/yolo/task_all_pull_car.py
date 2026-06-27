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

from mqtt_common import require_done, run_ee_offsets, run_gripper, run_whole_body_json, safe_motion_mode, submit_task


TASK_SEQUENCE = [
    "python mqtt_mp3.py --file JPCH5.mp3",

    "python ../BOX_528_1/move_gopullcar.py",
    "python ../Robot/move_ee_pose_open_2.py",
    "python move_whole_body_by_json.py ../positions/car_grab_5.json",
    "python move_whole_body_by_json.py ../positions/car_grab_4.json",
    "python offset_move_car_grab.py",
    "python ../BOX_528_1/move_pullcar.py",
    "python move_whole_body_by_json.py ../positions/car_grab_4.json",
    "python move_whole_body_by_json.py ../positions/car_grab_5.json",
    "python move_whole_body_by_json.py ../positions/pick_standby.json",

    "python ../BOX_528_1/move_gopullcarb.py",
    "python ../Robot/move_ee_pose_open_2.py",
    "python move_whole_body_by_json.py ../positions/car_grab_5.json",
    "python move_whole_body_by_json.py ../positions/car_grab_4.json",
    "python offset_move_car_grab.py",
    "python mqtt_mp3.py --file JPCH6.mp3"
    "python ../BOX_528_1/move_pullcarb.py",
    "python move_whole_body_by_json.py ../positions/car_grab_4.json",
    "python move_whole_body_by_json.py ../positions/car_grab_5.json",
    "python move_whole_body_by_json.py ../positions/pick_standby.json",
]


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Fast MQTT/Gateway sequence wrapper for yolo/task_all_pull_car.py")
    parser.add_argument("--execute", action="store_true", help="execute the fast in-process MQTT sequence; default prints plan")
    args = parser.parse_args()
    print("# yolo/task_all_pull_car.py")
    print(f"# steps={len(TASK_SEQUENCE)}, mode={'fast_execute' if args.execute else 'dry-run plan'}")
    for index, entry in enumerate(TASK_SEQUENCE, 1):
        print(f"[{index:02d}/{len(TASK_SEQUENCE):02d}] {entry}")
    if not args.execute:
        return 0

    result = submit_task(
        "interaction.play_tts",
        {
            "text": "将执行空车拉走动作",
            "post_play_wait_s": 0.0,
            "source_script": "interaction/play_tts_cli.py",
            "fast_demo_path": True,
        },
        mode=safe_motion_mode(),
        timeout_s=8.0,
    )
    require_done(result)

    run_gripper("open", source_script="Robot/move_ee_pose_open_2.py", targets=None)
    run_whole_body_json("../positions/car_grab_5.json", source_script="yolo/move_whole_body_by_json.py")
    run_whole_body_json("../positions/car_grab_4.json", source_script="yolo/move_whole_body_by_json.py")
    run_ee_offsets(
        "yolo/offset_move_common.py",
        offset_l=(0.0, -0.02 * 5, 0.0),
        offset_r=(0.0, 0.02 * 5, 0.0),
    )
    run_whole_body_json("../positions/car_grab_4.json", source_script="yolo/move_whole_body_by_json.py")
    run_whole_body_json("../positions/car_grab_5.json", source_script="yolo/move_whole_body_by_json.py")
    run_whole_body_json("../positions/pick_standby.json", source_script="yolo/move_whole_body_by_json.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
