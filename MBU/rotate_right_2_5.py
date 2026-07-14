#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MBU 导航 - 底盘向右旋转 2.5 度
"""

import sys
import os
import math
import time

import agibot_gdk

BOX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "BOX_528_1")
sys.path.append(BOX_DIR)

from robot_controller import RobotController


def main():
    print("#" * 60)
    print("#   MBU 导航 - 底盘向右旋转 2.5 度 - 开始   #")
    print("#" * 60)

    # ── 初始化 GDK ───────────────────────────────────────────
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK 初始化失败")
        sys.exit(1)
    print("GDK 初始化成功")

    time.sleep(2)

    nav = RobotController()
    nav.list_waypoints()

    # ── 向右旋转 2.5 度 ──────────────────────────────────────
    yaw_rad = -math.radians(3)   # 右转为负
    print(f"\n向右旋转 2.5 度 (yaw_rad={yaw_rad:.6f})")
    if not nav.go_rel(yaw_rad=yaw_rad):
        print("❌ 旋转失败")
        sys.exit(1)
    print("✅ 旋转完成")
    time.sleep(1.0)

    # ── 释放 GDK ─────────────────────────────────────────────
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("⚠️ GDK 释放失败")
    else:
        print("GDK 释放成功")

    print("\n#   MBU 导航 - 底盘向右旋转 2.5 度 - 完成   #")
    print("#" * 60)


if __name__ == "__main__":
    main()
