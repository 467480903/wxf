#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本田现场总控程序
按照指定序列依次执行各子脚本，完成完整的抓取-放置流程。
"""

import subprocess
import sys
import os
import argparse
import shlex

# 当前脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 执行序列（按顺序）
TASK_SEQUENCE = [
    "python move_whole_body_by_json.py ../posoitions/p1.json",
    "python move_whole_body_by_json.py ../posoitions/arm_position_to_grab_2.json",
    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",
    "python offset_move_left_002.py",
    "python offset_move_left_002.py",
    "python move_ee_pose_open_05.py",
    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",   
    "python offset_move_downward_002.py",   
    "python ../Robot/move_ee_pose_open_2.py",    
    "python offset_move_pull_back.py",
    "python offset_move_down.py",
    "python move_whole_body_by_json.py ../posoitions/pick_standby.json",
]


def run_step(index, task_entry, extra_args=None):
    """执行单个子脚本

    task_entry 可以是纯脚本名，也可以是 "脚本名 参数1 参数2" 形式的字符串。
    extra_args 是命令行传入的额外参数，会追加到每个子脚本后面。
    """
    parts = shlex.split(task_entry)
    if not parts:
        print(f"[步骤 {index}/{len(TASK_SEQUENCE)}] 空的任务条目")
        return False

    script_name = parts[0]
    script_own_args = parts[1:]

    script_path = script_name if os.path.isabs(script_name) else os.path.join(SCRIPT_DIR, script_name)

    if not os.path.exists(script_path):
        print(f"[步骤 {index}/{len(TASK_SEQUENCE)}] 找不到脚本: {task_entry}")
        return False

    print("=" * 60)
    print(f"[步骤 {index}/{len(TASK_SEQUENCE)}] 开始执行: {task_entry}")
    if script_own_args:
        print(f"脚本自带参数: {script_own_args}")
    if extra_args:
        print(f"附加参数: {extra_args}")
    print("=" * 60)

    cmd = [sys.executable, script_path]
    cmd.extend(script_own_args)
    if extra_args:
        cmd.extend(extra_args)

    result = subprocess.run(
        cmd,
        cwd=SCRIPT_DIR,
    )

    if result.returncode != 0:
        print(f"[步骤 {index}/{len(TASK_SEQUENCE)}] 执行失败: {task_entry} (返回码: {result.returncode})")
        return False

    print(f"[步骤 {index}/{len(TASK_SEQUENCE)}] 执行完成: {task_entry}")
    print()
    return True


def main():
    parser = argparse.ArgumentParser(
        description="本田现场总控程序 - 按序列执行各子脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python all.py\n"
               "  python all.py --arg --speed 0.5\n"
               "  python all.py -- --debug --count 3\n",
    )
    parser.add_argument(
        "extra",
        nargs=argparse.REMAINDER,
        help="传递给每个子脚本的额外参数（建议在前面加 -- 分隔）",
    )
    args = parser.parse_args()

    extra_args = args.extra
    if extra_args and extra_args[0] == "--":
        extra_args = extra_args[1:]

    print("#" * 60)
    print("#        本田现场总控程序 - 开始执行        #")
    print("#" * 60)
    if extra_args:
        print(f"# 附加参数: {extra_args}")
        print("#" * 60)
    print()

    total = len(TASK_SEQUENCE)
    for i, task_entry in enumerate(TASK_SEQUENCE, start=1):
        success = run_step(i, task_entry, extra_args)
        if not success:
            print(f"序列在步骤 {i}/{total} ({task_entry}) 处中断！")
            sys.exit(1)

    print("#" * 60)
    print("#        本田现场总控程序 - 全部执行完成        #")
    print("#" * 60)


if __name__ == "__main__":
    main()
