#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本田现场总控程序
按照指定序列依次执行各命令行，完成完整的抓取-放置流程。
每条任务是一个完整的命令行字符串（以 python 开头）。
"""

import subprocess
import sys
import os
import shlex

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

TASK_SEQUENCE = [
    "python ../Robot/move_ee_pose_close_2.py",    
    "python move_whole_body_by_json.py ../positions/pick_standby.json",
    "python ../interaction/play_tts_cli.py 执行基于视觉模型的推理,通过识别两个销子,然后计算销子的中点,和销子的深度值,来计算机器人的腰部旋转值,和纵声偏移量,和水平偏移量",
    "python cam_get_head.py",
    "yolo-env/bin/python cam_get_head_send.py shelf.pt 1",
    "cp yolo_depth_result.json yolo_depth_result_2.json",
    "python correct_waist.py",
    "python cam_get_head.py",
    "yolo-env/bin/python cam_get_head_send.py shelf.pt 1",
    "cp yolo_depth_result.json yolo_depth_result_3.json",
    "python move_ee_pose_right_half.py",

    "python move_whole_body_by_json.py ../positions/place_b_2.json",
    "python move_whole_body_by_json.py ../positions/place_b_3.json",
    
    "mv yolo_depth_result_2.json yolo_depth_result.json",
    "python correct_waist.py",
    "python move_arm_by_json.py ../positions/place_b_4.json",
    "python offset_move_left_002.py",
    "python move_arm_by_json.py ../positions/place_b_5.json",

    "mv yolo_depth_result_3.json yolo_depth_result.json",

    
    "python offset_move_horizon_b.py",
    "python offset_move_vertical_b.py",


    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",

    "python move_ee_pose_open_05.py",
    "python offset_move_downward_002.py",
    "python offset_move_downward_002.py",

    "python ../Robot/move_ee_pose_open_2.py",    
    "python offset_move_pull_back.py",
    "python move_whole_body_by_json.py ../positions/pick_standby.json",
]


def run_step(index, task_entry):
    """执行单条命令行任务"""
    parts = shlex.split(task_entry)
    if not parts:
        print(f"[步骤 {index}/{len(TASK_SEQUENCE)}] 空的任务条目")
        return False

    if parts[0] in ("python", "python3"):
        parts[0] = sys.executable

    print("=" * 60)
    print(f"[步骤 {index}/{len(TASK_SEQUENCE)}] 开始执行: {task_entry}")
    print("=" * 60)

    result = subprocess.run(
        parts,
        cwd=SCRIPT_DIR,
    )

    if result.returncode != 0:
        print(f"[步骤 {index}/{len(TASK_SEQUENCE)}] 执行失败: {task_entry} (返回码: {result.returncode})")
        return False

    print(f"[步骤 {index}/{len(TASK_SEQUENCE)}] 执行完成: {task_entry}")
    print()
    return True


def main():
    print("#" * 60)
    print("#        本田现场总控程序 - 开始执行        #")
    print("#" * 60)
    print()

    total = len(TASK_SEQUENCE)
    for i, task_entry in enumerate(TASK_SEQUENCE, start=1):
        success = run_step(i, task_entry)
        if not success:
            print(f"序列在步骤 {i}/{total} ({task_entry}) 处中断！")
            sys.exit(1)

    print("#" * 60)
    print("#        本田现场总控程序 - 全部执行完成        #")
    print("#" * 60)


if __name__ == "__main__":
    main()
