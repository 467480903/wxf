import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)  # 等待机器人初始化

# 控制腰部位置（按照关节顺序：idx01_body_joint1 到 idx05_body_joint5）
# 数据来源：之前日志中 idx01 ~ idx05 的 位置(弧度)
waist_positions = [
    -0.698,  # idx01_body_joint1
    1.571,   # idx02_body_joint2
    -0.872,  # idx03_body_joint3
    0.000,   # idx04_body_joint4
    0.000    # idx05_body_joint5
] 

# 设定腰部运动的速度 (保持0.3弧度/秒，确保平稳过渡)
waist_velocities = [0.3, 0.3, 0.3, 0.3, 0.3]  

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