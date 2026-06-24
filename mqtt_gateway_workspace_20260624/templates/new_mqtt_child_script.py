#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Template for creating a new WXF MQTT child script.

这个文件是“新建 MQTT 子脚本”的模板，不是直接给现场跑的正式动作脚本。

正确使用方式：

1. 先复制模板，例如：
       cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
       cp templates/new_mqtt_child_script.py yolo/my_new_script.py

2. 打开复制出来的新文件，只改 main() 里面的动作顺序。

3. 新脚本只调用本文件下面 import 的 mqtt_common helper。
   子脚本自己不要连接机器人底层 SDK，不要做 SDK 初始化，不要做 SDK 释放。
   Gateway 服务里已经有长期会话，所有真实动作都从 MQTT 发给 Gateway。

4. 新脚本写完后，先检查、再 dry-run、最后 live：
       python3 test_mqtt_migration.py
       ./run_dry_script.sh yolo/my_new_script.py
       ./run_live_script.sh yolo/my_new_script.py

5. live 会让真机运动。只有现场确认安全、机器人离开充电、运动区域清空后才能跑。
"""
from __future__ import annotations

import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# 1. Locate mqtt_common
# ---------------------------------------------------------------------------
#
# 这段代码必须保留在每个新 MQTT 子脚本顶部。
#
# 为什么要这样写：
# - 新工作区里有多个目录：yolo/、BOX_528_1/、Robot/、templates/。
# - 新脚本可能放在任意一个子目录。
# - 直接写固定路径容易在换目录运行时找不到 mqtt_common。
# - 这里从当前脚本位置往父目录逐层找，找到 mqtt_common 后加入 sys.path。
#
# 现场人员只需要记住：
# - 新脚本必须放在 mqtt_gateway_workspace_20260624 下面。
# - 不要把这段删掉。
# - 不要把新脚本放回 /data/wxf/wxf/yolo 这类原始目录。
for _parent in Path(__file__).resolve().parents:
    _common = _parent / "mqtt_common"
    if _common.is_dir():
        sys.path.insert(0, str(_common))
        break
else:
    raise RuntimeError("mqtt_common not found; put this script under the MQTT workspace")


# ---------------------------------------------------------------------------
# 2. Import only MQTT helpers
# ---------------------------------------------------------------------------
#
# 这里只允许从 mqtt_common 导入 helper。
#
# 每个 helper 的含义：
#
# ROOT
#   当前 MQTT 工作区根目录，例如：
#   /data/wxf/wxf/mqtt_gateway_workspace_20260624
#
# run_nav_waypoints(...)
#   底盘按旧 waypoint index 导航。它会发布 nav.goto_pose MQTT 任务。
#
# run_head_named(...)
#   头部姿态。参数是弧度，helper 会转换成 Gateway 需要的角度字段。
#
# run_whole_body_json(...)
#   读取 positions 里的 JSON，一次提交头、腰、双臂姿态。
#
# run_arm_json(...)
#   读取 positions 里的 JSON，只提交双臂姿态。
#
# run_waist_json(...)
#   读取 positions 里的 JSON，只提交腰部姿态。
#
# run_gripper(...)
#   夹爪开/关。只在确认当前物料状态后使用。
#
# run_ee_offsets(...)
#   末端相对偏移，单位是米。偏移量要小，不要写大步长。
#
# 不要在这里导入机器人底层 SDK 包。
from mqtt_common import (  # noqa: E402
    ROOT,
    run_arm_json,
    run_ee_offsets,
    run_gripper,
    run_head_named,
    run_nav_waypoints,
    run_waist_json,
    run_whole_body_json,
)


# SOURCE_SCRIPT 会随 MQTT 任务一起发给 Gateway，用来记录“哪个脚本发出的动作”。
# 例如脚本路径是 yolo/my_new_script.py，Gateway 日志里也会看到这个来源。
# 这对后面排查“哪个脚本让机器人动了”很重要，所以不要删。
SOURCE_SCRIPT = str(Path(__file__).resolve().relative_to(ROOT))


def main() -> int:
    # -----------------------------------------------------------------------
    # 3. Edit this function after copying the template
    # -----------------------------------------------------------------------
    #
    # 模板本身故意不执行任何机器人动作。
    #
    # 复制成真实脚本以后，把下面两行 print 和 return 2 删除，
    # 然后按实际需要添加动作 helper。
    #
    # 典型写法：
    #
    #     def main() -> int:
    #         run_whole_body_json("../positions/pick_standby.json", SOURCE_SCRIPT)
    #         run_arm_json("../positions/pick_b_2.json", SOURCE_SCRIPT)
    #         run_gripper("close", SOURCE_SCRIPT)
    #         return 0
    #
    # 执行顺序非常重要：
    # - helper 会按代码顺序一个一个执行。
    # - 上一步失败时脚本会停止，不会继续执行后面的动作。
    # - 所以先写“准备姿态”，再写“靠近/抓取/放置/撤离”等动作。
    #
    # 路径怎么写：
    # - 如果脚本放在 yolo/ 下，positions 里的文件通常写 ../positions/xxx.json。
    # - 如果脚本放在 BOX_528_1/ 下，也是相对于该脚本所在目录写路径。
    # - run_live_script.sh / run_dry_script.sh 会自动 cd 到脚本所在目录。
    #
    # 新脚本规则：
    # 1. 子脚本不要直接连接机器人底层 SDK。
    # 2. 子脚本不要做 SDK 初始化或释放。
    # 3. 子脚本只调用 mqtt_common helper。
    # 4. 先 run_dry_script.sh，再 run_live_script.sh。
    #
    # live 前必须人工确认：
    # - 机器人不在充电/插枪状态。
    # - 运动区域清空。
    # - 当前姿态适合执行这个子脚本。
    # - 如果要抓/放物料，夹爪和物料状态是确定的。
    #
    print("This is a template. Copy it, edit main(), then run the copied script.")
    print(f"source_script={SOURCE_SCRIPT}")
    return 2


def examples_for_copy_paste_only() -> None:
    # -----------------------------------------------------------------------
    # 4. Copy-paste examples
    # -----------------------------------------------------------------------
    #
    # 这个函数不会被 main() 调用，只是给写脚本的人看例子。
    # 不要直接调用 examples_for_copy_paste_only()。
    #
    # 正确用法：
    # - 从下面复制你需要的某几行到 main()。
    # - 按真实任务顺序排列。
    # - 删除不需要的动作。
    #
    # 不要把所有例子一起复制到 main()。

    # 底盘导航：按旧脚本里的 waypoint index 走点。
    #
    # index:
    #   原来 RobotController.go(index) 里的 index。
    #
    # high_precision:
    #   False 表示普通导航。
    #   True 表示更高精度，Gateway 会用更紧的到点容差。
    #
    # 注意：
    # - 这会让底盘运动。
    # - live 前必须确认机器人已离开充电状态。
    # - 如果现场路径有人/线/障碍物，不要 live。
    run_nav_waypoints(SOURCE_SCRIPT, [{"index": 11, "high_precision": False}])

    # 头部姿态：参数单位是弧度。
    #
    # yaw_rad:
    #   左右转头。
    #
    # pitch_rad:
    #   上下俯仰。
    #
    # roll_rad:
    #   头部横滚，通常保持 0。
    #
    # helper 会把弧度转换成 Gateway 需要的角度字段。
    run_head_named(SOURCE_SCRIPT, yaw_rad=0.0, pitch_rad=0.0, roll_rad=0.0)

    # 全身 JSON 姿态：读取 positions 里的一个 JSON。
    #
    # 适合：
    # - 头、腰、双臂需要一起到某个已记录姿态。
    #
    # 路径：
    # - 如果脚本在 yolo/ 下，../positions/pick_standby.json 表示工作区 positions。
    #
    # 注意：
    # - 这个 helper 会按顺序提交头、腰、手臂动作。
    # - live 前确认当前姿态不会和环境/工装干涉。
    run_whole_body_json("../positions/pick_standby.json", SOURCE_SCRIPT)

    # 双臂 JSON 姿态：只控制双臂。
    #
    # 适合：
    # - 腰部/头部已经在正确位置。
    # - 只需要切换手臂姿态。
    #
    # 注意：
    # - JSON 里的关节值必须来自迁移后的 positions。
    # - 不要引用原始目录里不确定的 JSON。
    run_arm_json("../positions/pick_b_2.json", SOURCE_SCRIPT)

    # 腰部 JSON 姿态：只控制腰部。
    #
    # 适合：
    # - 只需要调整腰部。
    #
    # 注意：
    # - 腰部动作可能改变手臂末端空间位置。
    # - 夹着物料时要确认不会碰撞。
    run_waist_json("../positions/waist_to_put.json", SOURCE_SCRIPT)

    # 夹爪动作。
    #
    # run_gripper("open", ...):
    #   打开夹爪。
    #
    # run_gripper("close", ...):
    #   关闭夹爪。
    #
    # 注意：
    # - 单独跑夹爪前要确认手臂位置。
    # - 关闭夹爪前要确认物料位置正确。
    # - 打开夹爪前要确认物料下面有承托，不会掉落。
    run_gripper("open", SOURCE_SCRIPT)
    run_gripper("close", SOURCE_SCRIPT)

    # 末端相对偏移：单位是米。
    #
    # offset_l:
    #   左手末端偏移，格式是 (dx, dy, dz)。
    #
    # offset_r:
    #   右手末端偏移，格式是 (dx, dy, dz)。
    #
    # 例子里的 0.01 表示 1 厘米。
    #
    # 注意：
    # - 末端偏移建议从很小的值开始。
    # - 不要一次写大偏移。
    # - 如果当前末端姿态不确定，先不要 live。
    run_ee_offsets(SOURCE_SCRIPT, offset_l=(0.0, 0.0, 0.01), offset_r=(0.0, 0.0, 0.01))


# 程序入口。
# 保留这一段，Python 直接运行脚本时会进入 main()。
if __name__ == "__main__":
    raise SystemExit(main())
