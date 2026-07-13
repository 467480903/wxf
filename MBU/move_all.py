#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MBU 综合导航程序
组合关节运动、末端执行器控制、地图导航和相对运动，完成完整路径：
  前置: 按 MBU_default.json 执行全身关节运动
  0. 双手末端向后缩 0.2米
  1. 运动到位置6 → 左转90度
  2. 运动到位置5
  3. 后退1.3米 → 右转90度
  4. 运动到位置7
  5. 后退1.8米 → 运动到位置7
  6. 右转90度
  7. 运动到位置8
  8. 后退1.3米
  9. 运动到位置7
"""

import sys
import os
import math
import time
import json

import agibot_gdk

# 引入 BOX_528_1 下的机器人控制封装
BOX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "BOX_528_1")
sys.path.append(BOX_DIR)

from robot_controller import RobotController
from end_effector_controller import EndEffectorController


# ═══════════════════════════════════════════════════════════════
#  关节索引映射表
# ═══════════════════════════════════════════════════════════════

HEAD_JOINT_KEYS = [
    "idx11_head_joint1", "idx12_head_joint2", "idx13_head_joint3",
]

WAIST_JOINT_KEYS = [
    "idx01_body_joint1", "idx02_body_joint2", "idx03_body_joint3",
    "idx04_body_joint4", "idx05_body_joint5",
]

LEFT_ARM_JOINT_KEYS = [
    "idx21_arm_l_joint1", "idx22_arm_l_joint2", "idx23_arm_l_joint3",
    "idx24_arm_l_joint4", "idx25_arm_l_joint5", "idx26_arm_l_joint6",
    "idx27_arm_l_joint7",
]

RIGHT_ARM_JOINT_KEYS = [
    "idx61_arm_r_joint1", "idx62_arm_r_joint2", "idx63_arm_r_joint3",
    "idx64_arm_r_joint4", "idx65_arm_r_joint5", "idx66_arm_r_joint6",
    "idx67_arm_r_joint7",
]

HEAD_SPEED  = 0.3
WAIST_SPEED = 0.3
ARM_SPEED   = 0.2


def move_joints_from_json(robot, json_path: str) -> bool:
    """
    读取 JSON 关节配置并执行全身关节运动（头部 → 腰部 → 手臂）。

    Parameters
    ----------
    robot : agibot_gdk.Robot
        已初始化的 Robot 实例
    json_path : str
        JSON 文件路径

    Returns
    -------
    bool : True=成功
    """
    if not os.path.exists(json_path):
        print(f"❌ 找不到关节配置文件: {json_path}")
        return False

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"✅ 关节配置读取成功: {json_path}")

    def extract(keys):
        return [data.get(k, 0.0) for k in keys]

    # ── 1. 头部 ──
    head_pos = extract(HEAD_JOINT_KEYS)
    head_vel = [HEAD_SPEED] * len(head_pos)
    print(f"  头部 → {[f'{p:.3f}' for p in head_pos]}")
    try:
        robot.move_head_joint(head_pos, head_vel)
        print("  ✅ 头部控制成功")
    except Exception as e:
        print(f"  ❌ 头部控制失败: {e}")
        return False
    time.sleep(0.2)

    # ── 2. 腰部 ──
    waist_pos = extract(WAIST_JOINT_KEYS)
    waist_vel = [WAIST_SPEED] * len(waist_pos)
    print(f"  腰部 → {[f'{p:.3f}' for p in waist_pos]}")
    try:
        robot.move_waist_joint(waist_pos, waist_vel)
        print("  ✅ 腰部控制成功")
    except Exception as e:
        print(f"  ❌ 腰部控制失败: {e}")
        return False
    time.sleep(0.2)

    # ── 3. 手臂（左7 + 右7 = 14，同时控制）──
    left_arm_pos  = extract(LEFT_ARM_JOINT_KEYS)
    right_arm_pos = extract(RIGHT_ARM_JOINT_KEYS)
    arm_positions = left_arm_pos + right_arm_pos
    arm_velocities = [ARM_SPEED] * len(arm_positions)
    print(f"  左臂 → {[f'{p:.3f}' for p in left_arm_pos]}")
    print(f"  右臂 → {[f'{p:.3f}' for p in right_arm_pos]}")
    try:
        robot.move_arm_joint(arm_positions, arm_velocities, 2)
        print("  ✅ 手臂控制成功")
    except Exception as e:
        print(f"  ❌ 手臂控制失败: {e}")
        return False

    return True


def main():
    print("#" * 60)
    print("#        MBU 综合导航 - 开始        #")
    print("#" * 60)

    # ── 初始化 GDK ───────────────────────────────────────────
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK 初始化失败")
        sys.exit(1)
    print("GDK 初始化成功")

    # ── 初始化机器人实例（用于关节运动和末端控制）──────────
    robot = agibot_gdk.Robot()
    time.sleep(2)   # 等待机器人就绪

    # ── 初始化末端执行器控制器 ───────────────────────────────
    ee_ctrl = EndEffectorController(robot)

    # ── 初始化导航控制器 ────────────────────────────────────
    nav = RobotController()
    nav.list_waypoints()

    # ── 前置步骤：按 MBU_default.json 执行全身关节运动 ──────
    json_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "positions", "MBU_default.json"
    )
    print("\n[前置步骤] 按 MBU_default.json 执行全身关节运动")
    if not move_joints_from_json(robot, json_path):
        print("❌ 关节运动失败，中止流程")
        sys.exit(1)
    print("✅ 全身关节运动完成")
    time.sleep(2.0)   # 等待关节运动到位

    # ── 步骤 0：双手末端向后缩 0.2米 ─────────────────────────
    print("\n[步骤 0/9] 双手末端向后缩 0.2 米")
    # 坐标系：X+(向前)，Y+(向左)，Z+(向上)
    # 向后缩 = X 负方向
    if not ee_ctrl.adjust_arms_relative(offset_l=(-0.2, 0, 0),
                                        offset_r=(-0.2, 0, 0)):
        print("❌ 双手末端后缩失败，中止流程")
        sys.exit(1)
    print("✅ 双手末端已后缩 0.2 米")
    time.sleep(1.0)

    # ── 步骤 1：运动到位置6，然后左转90度 ─────────────────────
    print("\n[步骤 1/9] 运动到位置 6")
    if not nav.go(6):
        print("❌ 运动到位置 6 失败，中止流程")
        sys.exit(1)
    print("✅ 已到达位置 6，准备左转 90 度")
    time.sleep(1.0)
    nav.go_rel(yaw_rad=math.pi / 2)    # 左转90度
    time.sleep(1.0)

    # ── 步骤 2：运动到位置5 ──────────────────────────────────
    print("\n[步骤 2/9] 运动到位置 5")
    if not nav.go(5):
        print("❌ 运动到位置 5 失败，中止流程")
        sys.exit(1)
    print("✅ 已到达位置 5")
    time.sleep(1.0)

    # ── 步骤 3：后退1.3米，然后右转90度 ──────────────────────
    print("\n[步骤 3/9] 后退 1.3 米")
    nav.go_rel(dx=-1.3)                # 后退1.3米
    time.sleep(1.0)
    print("  准备右转 90 度")
    nav.go_rel(yaw_rad=-math.pi / 2)   # 右转90度
    time.sleep(1.0)

    # ── 步骤 4：运动到位置7 ──────────────────────────────────
    print("\n[步骤 4/9] 运动到位置 7")
    if not nav.go(7):
        print("❌ 运动到位置 7 失败，中止流程")
        sys.exit(1)
    print("✅ 已到达位置 7")
    time.sleep(1.0)

    # ── 步骤 5：后退1.8米，再运动到位置7 ─────────────────────
    print("\n[步骤 5/9] 后退 1.8 米")
    nav.go_rel(dx=-1.8)                # 后退1.8米
    time.sleep(1.0)
    print("  再次运动到位置 6")
    if not nav.go(6):
        print("❌ 运动到位置 6 失败，中止流程")
        sys.exit(1)
    print("✅ 已到达位置 6")
    time.sleep(1.0)

    # ── 步骤 6：右转90度 ─────────────────────────────────────
    print("\n[步骤 6/9] 右转 90 度")
    nav.go_rel(yaw_rad=-math.pi / 2)   # 右转90度
    time.sleep(1.0)

    # ── 步骤 7：运动到位置8 ──────────────────────────────────
    print("\n[步骤 7/9] 运动到位置 8")
    if not nav.go(8):
        print("❌ 运动到位置 8 失败，中止流程")
        sys.exit(1)
    print("✅ 已到达位置 8")
    time.sleep(1.0)

    # ── 步骤 8：后退1.3米 ────────────────────────────────────
    print("\n[步骤 8/9] 后退 1.3 米")
    nav.go_rel(dx=-1.3)                # 后退1.3米
    time.sleep(1.0)

    # ── 步骤 9：运动到位置7 ──────────────────────────────────
    print("\n[步骤 9/9] 运动到位置 6")
    if not nav.go(6):
        print("❌ 运动到位置 6 失败，中止流程")
        sys.exit(1)
    print("✅ 已到达位置 6")

    # ── 释放 GDK ─────────────────────────────────────────────
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("⚠️ GDK 释放失败")
    else:
        print("GDK 释放成功")

    print("\n#" * 0)
    print("#        MBU 综合导航 - 全部完成        #")
    print("#" * 60)


if __name__ == "__main__":
    main()
