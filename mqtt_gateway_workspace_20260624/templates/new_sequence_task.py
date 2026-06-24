#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Template for a task-level MQTT sequence.

这个模板适合把多个已经迁移好的子脚本串起来，做成一个新的总控。

核心规则：
  - TASK_SEQUENCE 里只能写当前 MQTT 工作区内的脚本或简单 cp/mv。
  - 不要引用原始目录脚本。
  - 不要写 shell 管道、重定向、后台任务。
  - 默认只打印计划；加 --execute 才真正按顺序执行。

运行方式：
  cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
  python3 my_sequence.py
  python3 my_sequence.py --execute

更推荐用根目录启动器跑 live：
  cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
  ./run_live_script.sh yolo/my_sequence.py --execute
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


for _parent in Path(__file__).resolve().parents:
    _common = _parent / "mqtt_common"
    if _common.is_dir():
        sys.path.insert(0, str(_common))
        break
else:
    raise RuntimeError("mqtt_common not found; put this script under the MQTT workspace")

from mqtt_common import run_sequence  # noqa: E402


# 把要串起来的步骤写在这里。
#
# 每一行会按顺序执行：
#   1. 上一步成功，才会跑下一步。
#   2. 上一步失败，总控立刻停止并返回失败。
#   3. 路径必须留在 MQTT 工作区内。
#
# 例子：
#   "python move_whole_body_by_json.py ../positions/pick_standby.json"
#   "python ../BOX_528_1/move-pick2.py"
#   "python ../Robot/move_ee_pose_close_2.py"
TASK_SEQUENCE = [
    "python move_whole_body_by_json.py ../positions/pick_standby.json",
    # "python ../BOX_528_1/move-pick2.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="MQTT sequence task template")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="execute the migrated scripts; default only prints the plan",
    )
    args = parser.parse_args()

    return run_sequence(
        "templates/new_sequence_task.py",
        TASK_SEQUENCE,
        Path(__file__).resolve().parent,
        execute=args.execute,
    )


if __name__ == "__main__":
    raise SystemExit(main())
