"""
BOX_528_1 总控程序
按顺序执行7根棒的抓取-放置流程
"""

import subprocess
import sys
import os

# 脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 每根棒对应的 grab_above 脚本名
GRAB_SCRIPTS = [
    "move_arm_by_json_grab_above_第一根.py",
    "move_arm_by_json_grab_above_第二根.py",
    "move_arm_by_json_grab_above_第三根.py",
    "move_arm_by_json_grab_above_第四根.py",
    "move_arm_by_json_grab_above_第五根.py",
    "move_arm_by_json_grab_above_第六根.py",
    "move_arm_by_json_grab_above_第七根.py",
]


def build_round_steps(grab_script):
    """根据当前棒的 grab 脚本，构建一轮完整的执行步骤"""
    return [
        "move-ready1.py",
        "move_waist_by_json_default.py",
        "move_ee_pose_open_2.py",
        grab_script,                          # 每根棒不同的抓取位置
        "move-pick1.py",
        "move_ee_pose_close_2.py",
        "offset_move_pull.py",
        "move-adjust1.py",
        "move_arm_by_json_grab_above_2.py",
        "move-put1.py",
        "offset_move_down.py",
        "move_ee_pose_open_2.py",
        "offset_move_pull.py",
        "move-back.py",
    ]


def run_script(script_name):
    """执行单个脚本，失败时终止整个流程"""
    script_path = os.path.join(SCRIPT_DIR, script_name)
    print(f"\n{'='*60}")
    print(f"[执行] {script_name}")
    print(f"{'='*60}")

    if not os.path.exists(script_path):
        print(f"[错误] 脚本不存在: {script_path}")
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, script_path],
        cwd=SCRIPT_DIR,
    )

    if result.returncode != 0:
        print(f"[错误] {script_name} 执行失败，返回码: {result.returncode}")
        sys.exit(result.returncode)

    print(f"[完成] {script_name}")


def main():
    print("=" * 60)
    print("  BOX_528_1 总控程序启动")
    print(f"  共 {len(GRAB_SCRIPTS)} 根棒需要处理")
    print("=" * 60)

    for i, grab_script in enumerate(GRAB_SCRIPTS, 1):
        print(f"\n{'#'*60}")
        print(f"  第 {i}/{len(GRAB_SCRIPTS)} 根棒")
        print(f"{'#'*60}")

        steps = build_round_steps(grab_script)
        for step in steps:
            run_script(step)

    print("\n" + "=" * 60)
    print("  所有任务执行完毕！")
    print("=" * 60)


if __name__ == "__main__":
    main()
