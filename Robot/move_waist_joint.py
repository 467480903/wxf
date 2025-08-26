import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)  # 等待机器人初始化

# 控制腰部位置（按照关节顺序：idx01_body_joint1, idx02_body_joint2, idx03_body_joint3, idx04_body_joint4, idx05_body_joint5）
waist_positions = [0.0, 0.0, 0.0, 0.0, 0.0]  # 腰部关节位置列表
waist_velocities = [0.3, 0.3, 0.3, 0.3, 0.3]  # 腰部关节速度列表

try:
    result = robot.move_waist_joint(waist_positions, waist_velocities)
    print("腰部控制成功")
except Exception as e:
    print(f"腰部控制失败: {e}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")