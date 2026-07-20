"""
拍视频程序
执行序列：offset_move_down.py → move_ee_pose_open_2.py → offset_move_pull.py
"""

import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    "offset_move_down.py",
    "move_ee_pose_open_2.py",
    "offset_move_pull.py",
]


def run_script(script_name):
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
    print("  拍视频程序启动")
    print("=" * 60)

    for step in STEPS:
        run_script(step)

    print("\n" + "=" * 60)
    print("  执行完毕！")
    print("=" * 60)


if __name__ == "__main__":
    main()
