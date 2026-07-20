#!/usr/bin/env python3
"""
main_pipeline.py
13步总控程序：工件孔位抓取全流程

步骤:
 1. 移动到待命位姿 (pick_standby.json)
 2. 拍摄头部彩色+深度图像 (cam_get_head.py)
 3. YOLO检测孔位 (yolo_depth.py holes.pt) → holes_result.json
 4. 腰部转角对齐 (waist.py, 读 holes_result.json)
 5. 再次拍摄 (cam_get_head.py)
 6. 再次YOLO检测孔位 (yolo_depth.py holes.pt) → holes_result.json (更新)
 7. 水平偏移对齐 (offset_move_horizon.py, 读 holes_result.json + hands_pick_result.json)
 8. YOLO检测手指 (yolo_depth.py hands_pick.pt) → hands_pick_result.json
 9. 水平偏移修正 (offset_move_horizon.py, 读 holes_result.json + hands_pick_result.json)
10. 夹爪闭合 (move_ee_pose_close_2.py)
11. 插入 (offset_move_insert.py)
12. 拉回 (offset_move_pull_back.py)
13. 夹爪张开 (move_ee_pose_open_2.py)
"""

import os
import sys
import time
import subprocess
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
POSITIONS_DIR = os.path.join(PROJECT_DIR, "positions")
ROBOT_DIR = os.path.join(PROJECT_DIR, "Robot")

PICK_STANDBY_JSON = os.path.join(POSITIONS_DIR, "pick_standby.json")


def step_banner(step_num, total, desc):
    print("\n")
    print("█" * 70)
    print(f"  步骤 {step_num}/{total}: {desc}")
    print("█" * 70)


def run_script(script_path, args=None, cwd=None):
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    if cwd is None:
        cwd = SCRIPT_DIR
    print(f"  执行: {' '.join(cmd)}")
    print(f"  工作目录: {cwd}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"  ❌ 脚本返回非零退出码: {result.returncode}")
        return False
    print(f"  ✅ 完成")
    return True


def confirm_continue(step_num, desc):
    print(f"\n  ⏸  步骤 {step_num} ({desc}) 已完成，按 Enter 继续...")
    input()


def main():
    TOTAL_STEPS = 13

    print("=" * 70)
    print("  工件孔位抓取 — 13步全流程")
    print("=" * 70)
    print(f"  脚本目录: {SCRIPT_DIR}")
    print(f"  位姿目录: {POSITIONS_DIR}")
    print(f"  机器人目录: {ROBOT_DIR}")
    print()

    # ── 步骤 1: 移动到待命位姿 ──
    step_banner(1, TOTAL_STEPS, "移动到待命位姿 (pick_standby.json)")
    if not run_script(
        os.path.join(SCRIPT_DIR, "move_whole_body_by_json.py"),
        args=[PICK_STANDBY_JSON]
    ):
        return
    confirm_continue(1, "移动到待命位姿")

    # ── 步骤 2: 拍摄头部彩色+深度图像 ──
    step_banner(2, TOTAL_STEPS, "拍摄头部彩色+深度图像")
    if not run_script(os.path.join(SCRIPT_DIR, "cam_get_head.py")):
        return
    confirm_continue(2, "拍摄图像")

    # ── 步骤 3: YOLO检测孔位 ──
    step_banner(3, TOTAL_STEPS, "YOLO检测孔位 (holes.pt) → holes_result.json")
    if not run_script(
        os.path.join(SCRIPT_DIR, "yolo_depth.py"),
        args=["holes.pt"]
    ):
        return
    confirm_continue(3, "YOLO检测孔位")

    # ── 步骤 4: 腰部转角对齐 ──
    step_banner(4, TOTAL_STEPS, "腰部转角对齐 (读 holes_result.json)")
    if not run_script(os.path.join(SCRIPT_DIR, "waist.py")):
        return
    confirm_continue(4, "腰部转角对齐")

    # ── 步骤 5: 再次拍摄 ──
    step_banner(5, TOTAL_STEPS, "再次拍摄头部彩色+深度图像")
    if not run_script(os.path.join(SCRIPT_DIR, "cam_get_head.py")):
        return
    confirm_continue(5, "再次拍摄")

    # ── 步骤 6: 再次YOLO检测孔位 ──
    step_banner(6, TOTAL_STEPS, "再次YOLO检测孔位 (holes.pt) → 更新 holes_result.json")
    if not run_script(
        os.path.join(SCRIPT_DIR, "yolo_depth.py"),
        args=["holes.pt"]
    ):
        return
    confirm_continue(6, "再次YOLO检测孔位")

    # ── 步骤 7: 水平偏移对齐 (第一次，仅用 holes_result.json) ──
    step_banner(7, TOTAL_STEPS, "水平偏移对齐 (基于 holes_result.json)")
    holes_json = os.path.join(SCRIPT_DIR, "holes_result.json")
    if not os.path.exists(holes_json):
        print(f"  ❌ 找不到 {holes_json}")
        return
    with open(holes_json, 'r') as f:
        holes_data = json.load(f)
    h_offset_holes = holes_data['h_offset']
    offset_m = h_offset_holes * 0.001
    print(f"  holes h_offset: {h_offset_holes:.2f} px → {offset_m:.6f} m")

    sys.path.insert(0, SCRIPT_DIR)
    from ee_controller import EndEffectorController, init_gdk, release_gdk

    robot, _ = init_gdk()
    if robot is None:
        return
    try:
        controller = EndEffectorController(robot)
        controller.adjust_arms_relative(offset_l=(offset_m, 0, 0), offset_r=(offset_m, 0, 0))
    except Exception as e:
        print(f"  ❌ 偏移执行失败: {e}")
        release_gdk()
        return
    release_gdk()
    confirm_continue(7, "水平偏移对齐")

    # ── 步骤 8: YOLO检测手指 ──
    step_banner(8, TOTAL_STEPS, "YOLO检测手指 (hands_pick.pt) → hands_pick_result.json")
    if not run_script(
        os.path.join(SCRIPT_DIR, "yolo_depth.py"),
        args=["hands_pick.pt"]
    ):
        return
    confirm_continue(8, "YOLO检测手指")

    # ── 步骤 9: 水平偏移修正 ──
    step_banner(9, TOTAL_STEPS, "水平偏移修正 (holes_result.json + hands_pick_result.json)")
    if not run_script(os.path.join(SCRIPT_DIR, "offset_move_horizon.py")):
        return
    confirm_continue(9, "水平偏移修正")

    # ── 步骤 10: 夹爪闭合 ──
    step_banner(10, TOTAL_STEPS, "夹爪闭合")
    if not run_script(os.path.join(ROBOT_DIR, "move_ee_pose_close_2.py")):
        return
    confirm_continue(10, "夹爪闭合")

    # ── 步骤 11: 插入 ──
    step_banner(11, TOTAL_STEPS, "插入 (双臂向前)")
    if not run_script(os.path.join(SCRIPT_DIR, "offset_move_insert.py")):
        return
    confirm_continue(11, "插入")

    # ── 步骤 12: 拉回 ──
    step_banner(12, TOTAL_STEPS, "拉回 (双臂向后+上)")
    if not run_script(os.path.join(SCRIPT_DIR, "offset_move_pull_back.py")):
        return
    confirm_continue(12, "拉回")

    # ── 步骤 13: 夹爪张开 ──
    step_banner(13, TOTAL_STEPS, "夹爪张开")
    if not run_script(os.path.join(ROBOT_DIR, "move_ee_pose_open_2.py")):
        return

    print("\n")
    print("=" * 70)
    print("  🎉 全部13步流程执行完毕！")
    print("=" * 70)


if __name__ == "__main__":
    main()
