#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MBU 导航 - 运动到位置9（move_all.py 步骤 8~9）
  步骤8: 后退1.3米
  步骤9: 运动到位置9
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
    print("#        MBU 导航 - 运动到位置9 - 开始        #")
    print("#" * 60)

    # ── 初始化 GDK ───────────────────────────────────────────
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK 初始化失败")
        sys.exit(1)
    print("GDK 初始化成功")

    time.sleep(2)

    nav = RobotController()
    nav.list_waypoints()

    # ── 步骤 8：后退1.3米 ────────────────────────────────────
    print("\n[步骤 8] 后退 1.3 米")
    nav.go_rel(dx=-1.3)                # 后退1.3米
    time.sleep(1.0)

    # ── 步骤 9：运动到位置9 ──────────────────────────────────
    print("\n[步骤 9] 运动到位置 9")
    if not nav.go(8):
        print("❌ 运动到位置 9 失败，中止流程")
        sys.exit(1)
    print("✅ 已到达位置 9")

    # ── 释放 GDK ─────────────────────────────────────────────
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("⚠️ GDK 释放失败")
    else:
        print("GDK 释放成功")

    print("\n#        MBU 导航 - 运动到位置9 - 完成        #")
    print("#" * 60)


if __name__ == "__main__":
    main()
