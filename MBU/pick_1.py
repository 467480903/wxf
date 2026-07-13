#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MBU 抓取程序 pick_1
  1. 按 MBU_pick_1.json 执行全身关节运动
  2. 左右手往前运动（右手前进30mm，左手前进50mm）
  3. 左右夹爪合拢
  4. 左右手抬起 100mm
  5. 左右手后退 0.2米
"""

import sys
import os
import time
import json

import agibot_gdk

# 引入 BOX_528_1 下的机器人控制封装
BOX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "BOX_528_1")
sys.path.append(BOX_DIR)

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
    """读取 JSON 关节配置并执行全身关节运动（头部 → 腰部 → 手臂）"""
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


def close_grippers(robot) -> bool:
    """合拢左右夹爪（position = 0）"""
    # ── 右夹爪 ──
    joint_states_right = agibot_gdk.JointStates()
    joint_states_right.group = "right_tool"
    joint_states_right.target_type = "omnipicker"

    joint_state_r = agibot_gdk.JointState()
    joint_state_r.position = 0          # 0 = 合拢
    joint_states_right.states = [joint_state_r]
    joint_states_right.nums = len(joint_states_right.states)

    try:
        robot.move_ee_pos(joint_states_right)
        print("  ✅ 右夹爪合拢成功")
    except Exception as e:
        print(f"  ❌ 右夹爪合拢失败: {e}")
        return False
    time.sleep(0.5)

    # ── 左夹爪 ──
    joint_states_left = agibot_gdk.JointStates()
    joint_states_left.group = "left_tool"
    joint_states_left.target_type = "omnipicker"

    joint_state_l = agibot_gdk.JointState()
    joint_state_l.position = 0          # 0 = 合拢
    joint_states_left.states = [joint_state_l]
    joint_states_left.nums = len(joint_states_left.states)

    try:
        robot.move_ee_pos(joint_states_left)
        print("  ✅ 左夹爪合拢成功")
    except Exception as e:
        print(f"  ❌ 左夹爪合拢失败: {e}")
        return False
    time.sleep(0.5)

    return True


def main():
    print("#" * 60)
    print("#        MBU 抓取程序 pick_1 - 开始        #")
    print("#" * 60)

    # ── 初始化 GDK ───────────────────────────────────────────
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK 初始化失败")
        sys.exit(1)
    print("GDK 初始化成功")

    # ── 初始化机器人实例 ─────────────────────────────────────
    robot = agibot_gdk.Robot()
    time.sleep(2)   # 等待机器人就绪

    # ── 初始化末端执行器控制器 ───────────────────────────────
    ee_ctrl = EndEffectorController(robot)

    # ── 步骤 1：按 MBU_pick_1.json 执行全身关节运动 ──────────
    json_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "positions", "MBU_pick_1.json"
    )
    print("\n[步骤 1/5] 按 MBU_pick_1.json 执行全身关节运动")
    if not move_joints_from_json(robot, json_path):
        print("❌ 关节运动失败，中止流程")
        sys.exit(1)
    print("✅ 全身关节运动完成")
    time.sleep(2.0)   # 等待关节运动到位

    # ── 步骤 2：左右手往前运动 ───────────────────────────────
    # 右手前进 30mm = 0.03m，左手前进 50mm = 0.05m
    # 坐标系：X+(向前)，Y+(向左)，Z+(向上)
    print("\n[步骤 2/5] 左右手往前运动（右手 +30mm，左手 +50mm）")
    if not ee_ctrl.adjust_arms_relative(offset_l=(0.05, 0, 0),   # 左手前进50mm
                                        offset_r=(0.03, 0, 0)):  # 右手前进30mm
        print("❌ 双手前伸失败，中止流程")
        sys.exit(1)
    print("✅ 双手前伸完成")
    time.sleep(1.0)

    # ── 步骤 3：左右夹爪合拢 ─────────────────────────────────
    print("\n[步骤 3/5] 左右夹爪合拢")
    if not close_grippers(robot):
        print("❌ 夹爪合拢失败，中止流程")
        sys.exit(1)
    print("✅ 夹爪已合拢")
    time.sleep(1.0)

    # ── 步骤 4：左右手抬起 100mm ─────────────────────────────
    # 抬起 = Z+ 方向，100mm = 0.1m
    print("\n[步骤 4/5] 左右手抬起 100mm")
    if not ee_ctrl.adjust_arms_relative(offset_l=(0, 0, 0.1),    # 左手抬起100mm
                                        offset_r=(0, 0, 0.1)):   # 右手抬起100mm
        print("❌ 双手抬起失败，中止流程")
        sys.exit(1)
    print("✅ 双手已抬起 100mm")
    time.sleep(1.0)

    # ── 步骤 5：左右手后退 0.2米 ─────────────────────────────
    # 后退 = X- 方向，0.2m
    print("\n[步骤 5/5] 左右手后退 0.2 米")
    if not ee_ctrl.adjust_arms_relative(offset_l=(-0.2, 0, 0),   # 左手后退0.2m
                                        offset_r=(-0.2, 0, 0)):  # 右手后退0.2m
        print("❌ 双手后退失败，中止流程")
        sys.exit(1)
    print("✅ 双手已后退 0.2 米")

    # ── 释放 GDK ─────────────────────────────────────────────
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("⚠️ GDK 释放失败")
    else:
        print("GDK 释放成功")

    print("\n#        MBU 抓取程序 pick_1 - 全部完成        #")
    print("#" * 60)


if __name__ == "__main__":
    main()
