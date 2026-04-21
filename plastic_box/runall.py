import subprocess
import sys
import time

def run_script(script_name, max_retries=1):
    """执行单个脚本，支持重试"""
    for attempt in range(max_retries):
        print(f"执行: {script_name} (尝试 {attempt + 1}/{max_retries})")
        
        try:
            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.stdout:
                print(result.stdout)
            
            if result.returncode == 0:
                print(f"✓ {script_name} 执行成功\n")
                return True
            else:
                print(f"✗ {script_name} 失败，错误信息:")
                print(result.stderr)
                
        except subprocess.TimeoutExpired:
            print(f"✗ {script_name} 执行超时")
        except Exception as e:
            print(f"✗ {script_name} 异常: {e}")
        
        if attempt < max_retries - 1:
            print(f"3秒后重试...\n")
            time.sleep(3)
    
    print(f"✗ {script_name} 最终失败\n")
    return False

# 主程序
scripts = ['/data/wxf/wxf_421/plastic_box/move_ee_pose_open_2.py',
           '/data/wxf/wxf_421/plastic_box/move_arm_by_json_grab_above.py',
           '/data/wxf/wxf_421/plastic_box/move_waist_by_json_down.py', 
           '/data/wxf/wxf_421/plastic_box/move_ee_pose_close_2.py', 
           '/data/wxf/wxf_421/plastic_box/offset_move_up.py', 
           '/data/wxf/wxf_421/plastic_box/move_waist_by_json_up.py',
           '/data/wxf/wxf_421/plastic_box/move_to_place.py',
           '/data/wxf/wxf_421/plastic_box/offset_move_down.py',
           '/data/wxf/wxf_421/plastic_box/move_ee_pose_open_2.py',
           '/data/wxf/wxf_421/plastic_box/offset_move_up.py', 
           '/data/wxf/wxf_421/plastic_box/move_to_pick.py',
           '/data/wxf/wxf_421/plastic_box/move_arm_by_json_default.py']
failed_scripts = []

for script in scripts:
    if not run_script(script):
        failed_scripts.append(script)

# 总结
if failed_scripts:
    print(f"执行失败的脚本: {', '.join(failed_scripts)}")
else:
    print("✓ 所有脚本执行成功！")