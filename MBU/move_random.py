#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MBU 随机运动循环
  步骤1: 腰部随机正转/反转 0~2 度
  步骤2: 底盘随机运动，前后 ±120mm，左右 ±320mm
  步骤3: 导航到位置 8 (nav.go(8))
  循环执行步骤 1 → 2 → 3
"""

import sys
import os
import math
import time
import random
import json

import agibot_gdk

BOX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "BOX_528_1")
sys.path.append(BOX_DIR)

from robot_controller import RobotController


# ═══════════════════════════════════════════════════════════════
#  腰部关节映射
# ═══════════════════════════════════════════════════════════════
WAIST_JOINT_KEYS = [
    "idx01_body_joint1", "idx02_body_joint2", "idx03_body_joint3",
    "idx04_body_joint4", "idx05_body_joint5",
]

# 腰部偏航关节（用于随机正/反转）
WAIST_YAW_JOINT_KEY = "idx05_body_joint5"

WAIST_SPEED = 0.3

# 腰部随机旋转幅度上限（度）
WAIST_ROT_MAX_DEG = 2.0

# 底盘随机运动幅度（米）
DX_RANGE = 0.1  # 前后 ±120mm
DY_RANGE = 0.1   # 左右 ±320mm


def get_default_waist_positions() -> dict:
    """从 MBU_default.json 读取腰部默认位置作为兜底基线"""
    json_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "positions", "MBU_default.json"
    )
    if not os.path.exists(json_path):
        return {}
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: data.get(k, 0.0) for k in WAIST_JOINT_KEYS}
    except Exception as e:
        print(f"  ⚠️ 读取默认关节配置失败: {e}")
        return {}


def get_current_waist_positions(robot) -> dict:
    """读取当前腰部 5 个关节位置，返回 dict {key: position}"""
    positions = {}
    try:
        joint_states = robot.get_joint_states()
        for joint in joint_states:
            if joint.name in WAIST_JOINT_KEYS:
                positions[joint.name] = joint.position
    except Exception as e:
        print(f"  ⚠️ 读取关节状态失败: {e}")
    return positions


def move_waist_random(robot) -> bool:
    """腰部随机正转/反转 0~2 度（仅偏航关节 idx01_body_joint1 叠加随机偏移）"""
    # 随机角度：方向随机，幅度 0~2 度
    angle_deg = random.uniform(0.0, WAIST_ROT_MAX_DEG)
    if random.random() < 0.5:
        angle_deg = -angle_deg
    angle_rad = math.radians(angle_deg)

    # 读取当前腰部关节位置；失败则回退到默认配置
    cur = get_current_waist_positions(robot)
    if not cur:
        print("  ⚠️ 未能读取当前腰部位置，使用 MBU_default.json 作为基线")
        cur = get_default_waist_positions()
    if not cur:
        print("  ❌ 无可用基线，跳过腰部旋转")
        return False

    # 构造目标位置：偏航关节加上随机偏移，其它关节保持当前
    target_pos = [cur.get(k, 0.0) for k in WAIST_JOINT_KEYS]
    yaw_idx = WAIST_JOINT_KEYS.index(WAIST_YAW_JOINT_KEY)
    cur_yaw = cur.get(WAIST_YAW_JOINT_KEY, 0.0)
    target_pos[yaw_idx] = cur_yaw + angle_rad

    vel = [WAIST_SPEED] * len(target_pos)
    print(f"  {WAIST_YAW_JOINT_KEY}: {cur_yaw:.4f} rad → {target_pos[yaw_idx]:.4f} rad "
          f"(Δ{angle_deg:+.2f}°)")

    try:
        robot.move_waist_joint(target_pos, vel)
        print("  ✅ 腰部控制成功")
    except Exception as e:
        print(f"  ❌ 腰部控制失败: {e}")
        return False
    return True


def chassis_random_move(nav) -> bool:
    """底盘随机运动：前后 ±120mm，左右 ±320mm，随机旋转 0~2 度"""
    dx = random.choice([-DX_RANGE, DX_RANGE])
    dy = random.choice([-DY_RANGE, DY_RANGE])
    yaw_deg = random.uniform(0.0, 2.0)
    if random.random() < 0.5:
        yaw_deg = -yaw_deg
    yaw_rad = math.radians(yaw_deg)
    print(f"  底盘随机运动: dx={dx*1000:+.0f}mm  dy={dy*1000:+.0f}mm  yaw={yaw_deg:+.2f}°")
    return nav.go_rel(dx=dx, dy=dy, yaw_rad=yaw_rad)


def main():
    print("#" * 60)
    print("#        MBU 随机运动循环 - 开始        #")
    print("#" * 60)

    # ── 初始化 GDK ───────────────────────────────────────────
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK 初始化失败")
        sys.exit(1)
    print("GDK 初始化成功")

    robot = agibot_gdk.Robot()
    time.sleep(2)

    nav = RobotController()
    nav.list_waypoints()

    cycle = 0
    try:
        while True:
            cycle += 1
            print("\n" + "=" * 60)
            print(f"  循环 #{cycle} 开始")
            print("=" * 60)

            # ── 步骤 1：腰部随机正/反转 0~2 度 ─────────────────
            print("\n[步骤 1] 腰部随机旋转")
            move_waist_random(robot)
            time.sleep(1.0)

            # ── 步骤 2：底盘随机运动 ──────────────────────────
            print("\n[步骤 2] 底盘随机运动")
            chassis_random_move(nav)
            time.sleep(1.0)

            # ── 步骤 3：导航到位置 8 ──────────────────────────

            if not nav.go(9):
                print("❌ 导航到位置 9 失败，继续下一循环")
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断，退出循环")

    # ── 释放 GDK ─────────────────────────────────────────────
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("⚠️ GDK 释放失败")
    else:
        print("GDK 释放成功")

    print("\n#        MBU 随机运动循环 - 结束        #")
    print("#" * 60)


if __name__ == "__main__":
    main()
