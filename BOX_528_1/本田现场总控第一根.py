#!/usr/bin/env python3
"""
本田现场总控程序 - 第一根
按顺序执行以下脚本：
1. move-ready1.py          - 导航到准备点
2. move_ee_pose_open_2.py  - 张开夹爪
3. move_arm_by_json_grab_第一根.py - 手臂移动到抓取位置
4. move-pick1.py           - 导航到抓取点
5. move_ee_pose_close_2.py - 闭合夹爪
6. offset_move_up.py       - 手臂上抬
7. offset_move_pull.py     - 手臂后拉
8. move-adjust1.py         - 导航调整
9. move-put1.py            - 导航到放置点
"""

import subprocess
import sys
import os

# 脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 按顺序定义执行序列
TASK_SEQUENCE = [
    "move-ready1.py",
    "move_ee_pose_open_2.py",
    "move_arm_by_json_grab_第一根.py",
    "move-pick1.py",
    "move_ee_pose_close_2.py",
    "offset_move_up.py",
    "offset_move_pull.py",
    "move-adjust1.py",
    "move-put1.py",
]


def run_script(script_name):
    """执行单个脚本，返回是否成功"""
    script_path = os.path.join(SCRIPT_DIR, script_name)

    if not os.path.exists(script_path):
        print(f"[错误] 脚本不存在: {script_path}")
        return False

    print(f"\n{'='*60}")
    print(f"[执行] {script_name}")
    print(f"{'='*60}")

    result = subprocess.run(
        [sys.executable, script_path],
        cwd=SCRIPT_DIR,
    )

    if result.returncode != 0:
        print(f"[失败] {script_name} 返回码: {result.returncode}")
        return False

    print(f"[完成] {script_name}")
    return True


def main():
    print("=" * 60)
    print("  本田现场总控程序 - 第一根  开始执行")
    print("=" * 60)

    total = len(TASK_SEQUENCE)
    success_count = 0

    for i, script_name in enumerate(TASK_SEQUENCE, 1):
        print(f"\n>>> 步骤 {i}/{total}: {script_name}")
        if not run_script(script_name):
            print(f"\n[中断] 步骤 {i} 失败，总控程序终止")
            break
        success_count += 1

    print(f"\n{'='*60}")
    print(f"  执行完毕: {success_count}/{total} 步成功")
    if success_count < total:
        print(f"  [警告] 有 {total - success_count} 步未执行")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
