#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Template for a chassis-only MQTT script.

这个模板适合只做底盘导航的子脚本。

使用方法：
  1. cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
  2. cp templates/new_nav_script.py yolo/my_nav_task.py
  3. 打开 yolo/my_nav_task.py，只改 main() 里的 waypoint index。
  4. python3 test_mqtt_migration.py
  5. ./run_dry_script.sh yolo/my_nav_task.py
  6. 现场确认安全后：./run_live_script.sh yolo/my_nav_task.py

注意：
  - 子脚本只调用 MQTT helper。
  - 不要把这个文件复制回原始 /data/wxf/wxf/yolo 目录。
  - live 会让底盘真实运动。
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

from mqtt_common import ROOT, run_nav_waypoints  # noqa: E402


SOURCE_SCRIPT = str(Path(__file__).resolve().relative_to(ROOT))


def main() -> int:
    # 模板默认不让机器人运动，防止现场直接跑模板。
    # 复制成正式脚本后，把下面两行删除，再取消 run_nav_waypoints 的注释。
    print("This is a navigation template. Copy it and edit main() before running live.")
    return 2

    # waypoint index 来自旧 RobotController.go(index) 的 index。
    # high_precision=False:
    #   普通导航，容差较宽，适合大多数去点。
    # high_precision=True:
    #   更高精度到点，速度和容差更保守，适合靠近工装或料架前的最后一点。
    #
    # 可以写多个点，helper 会按列表顺序一个一个提交。
    # 任意一个点失败，脚本会停止，不会继续跑后面的点。
    run_nav_waypoints(
        SOURCE_SCRIPT,
        [
            {"index": 11, "high_precision": False},
            # {"index": 12, "high_precision": True},
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
