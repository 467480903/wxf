#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO 导航 - 底盘纠正：先按 angle_rad 旋转，再按 horizontal_offset_px 左右平移
"""

import sys
import os
import time
import json

import agibot_gdk

BOX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "BOX_528_1")
sys.path.append(BOX_DIR)

from robot_controller import RobotController

# ── 配置 ───────────────────────────────────────────────────
RESULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yolo_depth_result.json")

# 像素 → 毫米 的换算系数（暂定）
PX_TO_MM = 10


def main():
    print("#" * 60)
    print("#   YOLO 导航 - 底盘纠正（旋转 + 平移）- 开始   #")
    print("#" * 60)

    # ── 读取 angle_rad 与 horizontal_offset_px ─────────────
    if not os.path.exists(RESULT_FILE):
        print(f"❌ 找不到结果文件：{RESULT_FILE}")
        sys.exit(1)
    with open(RESULT_FILE, "r", encoding="utf-8") as f:
        result = json.load(f)

    angle_rad = result.get("angle_rad")
    if angle_rad is None:
        print("❌ 结果文件中未找到 angle_rad 字段")
        sys.exit(1)
    offset_px = result.get("horizontal_offset_px")
    if offset_px is None:
        print("❌ 结果文件中未找到 horizontal_offset_px 字段")
        sys.exit(1)

    print(f"📐 从 {os.path.basename(RESULT_FILE)} 读取：")
    print(f"   angle_rad = {angle_rad}")
    print(f"   horizontal_offset_px = {offset_px}")

    # ── 计算旋转量 ─────────────────────────────────────────
    yaw_rad = angle_rad * 1.8 * (-1)

    # ── 计算平移量（毫米）──────────────────────────────────
    move_mm = offset_px * PX_TO_MM
    # go_rel 的 dy：正=左，负=右，故取反
    dy_m = move_mm / 1000.0
    print(f"   换算：yaw_rad={yaw_rad:.6f}rad，"
          f"{offset_px}px × {PX_TO_MM} = {move_mm}mm → dy={dy_m:.6f}m")

    # ── 初始化 GDK ───────────────────────────────────────────
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK 初始化失败")
        sys.exit(1)
    print("GDK 初始化成功")

    time.sleep(2)

    nav = RobotController()
    nav.list_waypoints()

    # ── 第一步：按 angle_rad 旋转底盘 ────────────────────────
    print(f"\n[1/2] 底盘旋转 (yaw_rad={yaw_rad:.6f})")
    if not nav.go_rel(yaw_rad=yaw_rad):
        print("❌ 旋转失败")
        sys.exit(1)
    print("✅ 旋转完成")
    time.sleep(1.0)

    # ── 第二步：按 horizontal_offset_px 左右平移 ────────────
    print(f"\n[2/2] 底盘左右平移 (dy={dy_m:.6f}m)")
    if not nav.go_rel(dy=dy_m):
        print("❌ 平移失败")
        sys.exit(1)
    print("✅ 平移完成")
    time.sleep(1.0)

    # ── 释放 GDK ─────────────────────────────────────────────
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("⚠️ GDK 释放失败")
    else:
        print("GDK 释放成功")

    print("\n#   YOLO 导航 - 底盘纠正（旋转 + 平移）- 完成   #")
    print("#" * 60)


if __name__ == "__main__":
    main()


