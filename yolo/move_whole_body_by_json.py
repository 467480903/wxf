#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全身关节控制 — 从 JSON 文件读取所有 22 个关节角度，
依次控制头部(3)、腰部(5)、左臂(7)、右臂(7) 全部电机。

JSON 文件应包含以下键（缺省用 0.0）：
  头部: idx11_head_joint1, idx12_head_joint2, idx13_head_joint3
  腰部: idx01_body_joint1 ~ idx05_body_joint5
  左臂: idx21_arm_l_joint1 ~ idx27_arm_l_joint7
  右臂: idx61_arm_r_joint1 ~ idx67_arm_r_joint7

用法:
  python move_whole_body_by_json.py                          # 使用默认 JSON 路径
  python move_whole_body_by_json.py /path/to/your/json       # 指定 JSON 路径
  python move_whole_body_by_json.py --sync                   # 同时移动全身
"""

import sys
import os
import time
import json
import argparse
import agibot_gdk


# ══════════════════════════════════════════════════
#  关节索引映射表（与 existing JSON 文件保持一致）
#  完整键名列表参见 positions/arm_default.json
# ══════════════════════════════════════════════════

HEAD_JOINT_KEYS = [
    "idx11_head_joint1",
    "idx12_head_joint2",
    "idx13_head_joint3",
]

WAIST_JOINT_KEYS = [
    "idx01_body_joint1",
    "idx02_body_joint2",
    "idx03_body_joint3",
    "idx04_body_joint4",
    "idx05_body_joint5",
]

LEFT_ARM_JOINT_KEYS = [
    "idx21_arm_l_joint1",
    "idx22_arm_l_joint2",
    "idx23_arm_l_joint3",
    "idx24_arm_l_joint4",
    "idx25_arm_l_joint5",
    "idx26_arm_l_joint6",
    "idx27_arm_l_joint7",
]

RIGHT_ARM_JOINT_KEYS = [
    "idx61_arm_r_joint1",
    "idx62_arm_r_joint2",
    "idx63_arm_r_joint3",
    "idx64_arm_r_joint4",
    "idx65_arm_r_joint5",
    "idx66_arm_r_joint6",
    "idx67_arm_r_joint7",
]

# 默认速度（弧度/秒）
HEAD_SPEED   = 0.3
WAIST_SPEED  = 0.3
ARM_SPEED    = 0.2


def read_json(file_path):
    """读取并解析 JSON 文件"""
    if not os.path.exists(file_path):
        print(f"❌ 找不到文件: {file_path}")
        sys.exit(1)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"✅ JSON 配置读取成功: {file_path}")
        return data
    except Exception as e:
        print(f"❌ 解析 JSON 文件失败: {e}")
        sys.exit(1)


def extract_positions(data, keys):
    """从字典中按 key 列表提取关节位置（缺失默认 0.0）"""
    return [data.get(key, 0.0) for key in keys]


def move_sequentially(robot, data):
    """
    顺序控制模式：头部 → 腰部 → 手臂（左臂+右臂同时）
    这样做可以避免同时发出过多指令，运动更可控。
    """
    # ── 1. 头部 (3个关节) ──
    head_pos = extract_positions(data, HEAD_JOINT_KEYS)
    head_vel = [HEAD_SPEED] * len(head_pos)
    print(f"\n🔹 头部  →  {[f'{p:.3f}' for p in head_pos]}")
    try:
        robot.move_head_joint(head_pos, head_vel)
        print("   ✅ 头部控制成功")
    except Exception as e:
        print(f"   ❌ 头部控制失败: {e}")
    time.sleep(0.2)  # 给执行器一点响应时间

    # ── 2. 腰部 (5个关节) ──
    waist_pos = extract_positions(data, WAIST_JOINT_KEYS)
    waist_vel = [WAIST_SPEED] * len(waist_pos)
    print(f"🔹 腰部  →  {[f'{p:.3f}' for p in waist_pos]}")
    try:
        robot.move_waist_joint(waist_pos, waist_vel)
        print("   ✅ 腰部控制成功")
    except Exception as e:
        print(f"   ❌ 腰部控制失败: {e}")
    time.sleep(0.2)

    # ── 3. 手臂 (左7 + 右7 = 14个关节，同时控制) ──
    left_arm_pos  = extract_positions(data, LEFT_ARM_JOINT_KEYS)
    right_arm_pos = extract_positions(data, RIGHT_ARM_JOINT_KEYS)
    arm_positions = left_arm_pos + right_arm_pos
    arm_velocities = [ARM_SPEED] * len(arm_positions)
    print(f"🔹 左臂  →  {[f'{p:.3f}' for p in left_arm_pos]}")
    print(f"🔹 右臂  →  {[f'{p:.3f}' for p in right_arm_pos]}")
    try:
        # move_arm_joint 第三个参数是时间系数（参考现有代码用 2）
        result = robot.move_arm_joint(arm_positions, arm_velocities, 2)
        print("   ✅ 手臂控制成功")
    except Exception as e:
        print(f"   ❌ 手臂控制失败: {e}")


def move_synchronously(robot, data):
    """
    同步控制模式：全身同时运动
    使用 joint_control_request API 一次性下发所有关节指令。
    参考自 Robot/mc_example.py 中的 JointPositionControl.publish_control_request。
    """
    # 全部 22 个关节的名称和位置
    all_joint_names = (
        HEAD_JOINT_KEYS +
        WAIST_JOINT_KEYS +
        LEFT_ARM_JOINT_KEYS +
        RIGHT_ARM_JOINT_KEYS
    )

    all_positions = [
        data.get(key, 0.0)
        for key in all_joint_names
    ]
    all_velocities = [0.3] * len(all_joint_names)

    print(f"\n🔹 全身同步控制 ({len(all_joint_names)} 个关节)")
    for name, pos in zip(all_joint_names, all_positions):
        print(f"   {name}: {pos:.4f}")

    try:
        req = agibot_gdk.JointControlReq()
        req.life_time = 1.0
        req.joint_names = all_joint_names
        req.joint_positions = all_positions
        req.joint_velocities = all_velocities
        robot.joint_control_request(req)
        print("✅ 全身同步控制成功！")
    except Exception as e:
        print(f"❌ 全身同步控制失败: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="全身关节控制 — 从 JSON 读取并控制所有 22 个电机"
    )
    parser.add_argument(
        "json_path",
        nargs="?",
        default=None,
        help="JSON 文件路径（默认: yolo/whole_body.json 或 positions/arm_default.json）"
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="全身同步运动（同时控制所有关节，而不是依次控制）"
    )
    args = parser.parse_args()

    # ── 确定 JSON 路径 ──
    json_path = args.json_path
    if json_path is None:
        # 默认优先查找 yolo/whole_body.json
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(script_dir, "whole_body.json"),
            os.path.join(os.path.dirname(script_dir), "positions", "arm_default.json"),
        ]
        for c in candidates:
            if os.path.exists(c):
                json_path = c
                break
        if json_path is None:
            print("❌ 未找到默认 JSON 文件，请指定路径")
            print("   用法: python move_whole_body_by_json.py /path/to/your.json")
            sys.exit(1)

    # ── 读取 JSON ──
    pos_data = read_json(json_path)

    # ── 初始化 GDK ──
    print("🔄 初始化 GDK...")
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK 初始化失败")
        sys.exit(1)
    print("✅ GDK 初始化成功")

    robot = agibot_gdk.Robot()
    time.sleep(2)  # 等待机器人初始化

    # ── 执行运动控制 ──
    try:
        if args.sync:
            move_synchronously(robot, pos_data)
        else:
            move_sequentially(robot, pos_data)
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
    except Exception as e:
        print(f"❌ 程序出错: {e}")

    # ── 释放资源 ──
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK 释放失败")
    else:
        print("\n✅ GDK 释放成功")
    print("🏁 程序结束")


if __name__ == "__main__":
    main()
