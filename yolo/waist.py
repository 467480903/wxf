import agibot_gdk
import time
import json
import os

RESULT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "holes_result.json")

if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)

joint_states = robot.get_joint_states()
current_waist_positions = [0.0, 0.0, 0.0, 0.0, 0.0]
for state in joint_states['states']:
    name = state['name']
    if 'idx01_body_joint1' in name:
        current_waist_positions[0] = state['motor_position']
    elif 'idx02_body_joint2' in name:
        current_waist_positions[1] = state['motor_position']
    elif 'idx03_body_joint3' in name:
        current_waist_positions[2] = state['motor_position']
    elif 'idx04_body_joint4' in name:
        current_waist_positions[3] = state['motor_position']
    elif 'idx05_body_joint5' in name:
        current_waist_positions[4] = state['motor_position']

print(f"当前腰部位姿 (弧度): {[round(p, 4) for p in current_waist_positions]}")

if not os.path.exists(RESULT_JSON):
    print(f"❌ 找不到 {RESULT_JSON}，请先运行 yolo_depth.py holes.pt")
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("GDK释放失败")
    else:
        print("GDK释放成功")
    exit(1)

with open(RESULT_JSON, 'r') as f:
    result = json.load(f)

target_delta = result['angle_rad']
print(f"从 {RESULT_JSON} 读取转角: {target_delta:.4f} rad ({target_delta * 180 / 3.14159:.2f} deg)")

current_waist_positions[4] -= target_delta

waist_velocities = [0.3, 0.3, 0.3, 0.3, 0.3]

print(f"目标腰部位姿 (弧度): {[round(p, 4) for p in current_waist_positions]}")
print(f"idx05_body_joint5 转动量: {target_delta:.4f} rad ({target_delta * 180 / 3.14159:.2f} deg)")

try:
    result = robot.move_waist_joint(current_waist_positions, waist_velocities)
    print("腰部控制成功")
    print(f"idx05_body_joint5 已转动 {target_delta:.4f} rad")
except Exception as e:
    print(f"腰部控制失败: {e}")

if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")
