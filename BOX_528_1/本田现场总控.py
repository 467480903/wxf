#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本田现场总控程序
按照指定序列依次执行各子脚本，完成完整的抓取-放置流程。
"""

import subprocess
import sys
import os

# 当前脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 执行序列（按顺序）
TASK_SEQUENCE = [
    "move-ready1.py",
    "move_ee_pose_open_2.py",
    "move_arm_by_json_grab_above_第一根.py",
    "move-pick1.py",
    "move_ee_pose_close_2.py",
    "offset_move_up.py",
    "move-adjust1.py",
    "move_arm_by_json_grab_above_2.py",
    "move-put1.py",
    "offset_move_down.py",
    "move_ee_pose_open_2.py",
    "offset_move_pull.py",
    "move-back.py",
]


def run_step(index, script_name):
    """执行单个子脚本"""
    script_path = os.path.join(SCRIPT_DIR, script_name)

    if not os.path.exists(script_path):
        print(f"[步骤 {index}/{len(TASK_SEQUENCE)}] 找不到脚本: {script_name}")
        return False

    print("=" * 60)
    print(f"[步骤 {index}/{len(TASK_SEQUENCE)}] 开始执行: {script_name}")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, script_path],
        cwd=SCRIPT_DIR,
    )

    if result.returncode != 0:
        print(f"[步骤 {index}/{len(TASK_SEQUENCE)}] 执行失败: {script_name} (返回码: {result.returncode})")
        return False

    print(f"[步骤 {index}/{len(TASK_SEQUENCE)}] 执行完成: {script_name}")
    print()
    return True


def main():
    print("#" * 60)
    print("#        本田现场总控程序 - 开始执行        #")
    print("#" * 60)
    print()

    total = len(TASK_SEQUENCE)
    for i, script_name in enumerate(TASK_SEQUENCE, start=1):
        success = run_step(i, script_name)
        if not success:
            print(f"序列在步骤 {i}/{total} ({script_name}) 处中断！")
            sys.exit(1)

    print("#" * 60)
    print("#        本田现场总控程序 - 全部执行完成        #")
    print("#" * 60)


if __name__ == "__main__":
    main()
