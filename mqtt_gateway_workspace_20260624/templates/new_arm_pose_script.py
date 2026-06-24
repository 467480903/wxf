#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Template for an upper-body MQTT pose script.

这个模板适合只做头、腰、双臂、夹爪、末端小偏移的子脚本。

先复制再改：
  cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
  cp templates/new_arm_pose_script.py yolo/my_pose_task.py

然后先 dry-run：
  python3 test_mqtt_migration.py
  ./run_dry_script.sh yolo/my_pose_task.py

最后现场确认安全后才 live：
  ./run_live_script.sh yolo/my_pose_task.py
"""
from __future__ import annotations

import sys
from pathlib import Path


for _parent in Path(__file__).resolve().parents:
    _common = _parent / "mqtt_common"
    if _common.is_dir():
        sys.path.insert(0, str(_common))
        break
else:
    raise RuntimeError("mqtt_common not found; put this script under the MQTT workspace")

from mqtt_common import (  # noqa: E402
    ROOT,
    run_arm_json,
    run_ee_offsets,
    run_gripper,
    run_head_named,
    run_waist_json,
    run_whole_body_json,
)


SOURCE_SCRIPT = str(Path(__file__).resolve().relative_to(ROOT))


def main() -> int:
    # 模板默认退出，不做任何动作。
    # 复制成正式脚本后，把下面两行删除，再按现场任务取消需要的动作注释。
    print("This is a pose template. Copy it and edit main() before running live.")
    return 2

    # 全身姿态：头、腰、双臂按同一个 JSON 执行。
    # 路径相对于脚本所在目录；脚本放在 yolo/ 时，positions 写 ../positions/xxx.json。
    run_whole_body_json("../positions/pick_standby.json", SOURCE_SCRIPT)

    # 只动双臂。
    # 适合腰和头已经在正确位置，只需要切换手臂姿态。
    run_arm_json("../positions/pick_b_2.json", SOURCE_SCRIPT)

    # 只动腰。
    # 夹着物料时尤其要确认不会扫到工装。
    run_waist_json("../positions/waist_to_put.json", SOURCE_SCRIPT)

    # 只动头。单位是弧度。
    run_head_named(SOURCE_SCRIPT, yaw_rad=0.0, pitch_rad=0.0, roll_rad=0.0)

    # 夹爪打开/关闭。
    # 打开前确认物料不会掉；关闭前确认物料在夹爪范围内。
    run_gripper("open", SOURCE_SCRIPT)
    run_gripper("close", SOURCE_SCRIPT)

    # 末端相对偏移，单位是米。
    # 建议从 0.002 到 0.010 这种小量开始，不要一次写大偏移。
    run_ee_offsets(SOURCE_SCRIPT, offset_l=(0.0, 0.0, 0.005), offset_r=(0.0, 0.0, 0.005))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
