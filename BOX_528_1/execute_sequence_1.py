import subprocess
import os

import time
import agibot_gdk
from show_chassis_speed import ChassisSpeedMonitor

def execute_script(script_name):
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    print(f"正在执行: {script_name}")
    try:
        result = subprocess.run(['python', script_path],
                               capture_output=True,
                               text=True,
                               check=True)
        print(f"执行成功: {script_name}")
        if result.stdout:
            print(f"标准输出:\n{result.stdout}")
        if result.stderr:
            print(f"标准错误:\n{result.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"执行失败: {script_name}")
        print(f"错误码: {e.returncode}")
        print(f"标准输出:\n{e.stdout}")
        print(f"标准错误:\n{e.stderr}")
        raise

def main():
    scripts = [
        'move-pick1.py',
        'move_ee_pose_open_2.py',
        'move_arm_by_json_grab_above.py',
        'move_waist_by_json_down.py',
        'move_ee_pose_close_2.py',
        'offset_move_up.py',
        'move_waist_by_json_up.py',
        'move-put1.py',
        'move_waist_by_json_down.py',
        'offset_move_down.py',
        'move_ee_pose_open_2.py',
        'offset_move_up.py',
        'move_waist_by_json_up.py',
        'move_arm_by_json_default.py',
        'move_waist_by_json_default.py'


        
        
            ]

    print("开始依次执行脚本序列...")
    print("=" * 50)

    for script in scripts:
        execute_script(script)
        print("-" * 50)

    print("所有脚本执行完成！")

if __name__ == "__main__":
    main()