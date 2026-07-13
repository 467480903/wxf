#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MBU 导航 - 运动到位置8（move_all.py 步骤 2~7）
  步骤2: 运动到位置5（起点）
  步骤3: 后退1.3米 → 右转90度
  步骤4: 运动到位置7
  步骤5: 后退1.8米 → 运动到位置6
  步骤6: 右转90度
  步骤7: 运动到位置8
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
    print("#        MBU 导航 - 运动到位置8 - 开始        #")
    print("#" * 60)

    # ── 初始化 GDK ───────────────────────────────────────────
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK 初始化失败")
        sys.exit(1)
    print("GDK 初始化成功")

    time.sleep(2)

    nav = RobotController()
    nav.list_waypoints()

    # ── 步骤 2：运动到位置5（起点）──────────────────────────
    print("\n[步骤 2] 运动到位置 5")
    if not nav.go(5):
        print("❌ 运动到位置 5 失败，中止流程")
        sys.exit(1)
    print("✅ 已到达位置 5")
    time.sleep(1.0)

    # ── 步骤 3：后退1.3米，然后右转90度 ──────────────────────
    print("\n[步骤 3] 后退 1.3 米")
    nav.go_rel(dx=-1.3)                # 后退1.3米
    time.sleep(1.0)
    print("  准备右转 90 度")
    nav.go_rel(yaw_rad=-math.pi / 2)   # 右转90度
    time.sleep(1.0)

    # ── 步骤 4：运动到位置7 ──────────────────────────────────
    print("\n[步骤 4] 运动到位置 6")
    if not nav.go(6):
        print("❌ 运动到位置 6 失败，中止流程")
        sys.exit(1)
    print("✅ 已到达位置 6")
    time.sleep(1.0)

    # ── 步骤 5：后退1.8米，再运动到位置6 ─────────────────────
    time.sleep(1.0)
    print("  运动到位置 7")
    if not nav.go(7):
        print("❌ 运动到位置 7 失败，中止流程")
        sys.exit(1)
    print("✅ 已到达位置 7")
    time.sleep(1.0)



    # ── 释放 GDK ─────────────────────────────────────────────
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("⚠️ GDK 释放失败")
    else:
        print("GDK 释放成功")

    print("\n#        MBU 导航 - 运动到位置8 - 完成        #")
    print("#" * 60)


if __name__ == "__main__":
    main()
