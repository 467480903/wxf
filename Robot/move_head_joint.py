import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)  # 等待机器人初始化

# 控制头部位置（按照关节顺序：idx11_head_joint1, idx12_head_joint2, idx13_head_joint3）
head_positions = [0.05, 0.05, 0.05]  # 头部关节位置列表
head_velocities = [0.3, 0.3, 0.3]  # 头部关节速度列表

try:
    result = robot.move_head_joint(head_positions, head_velocities)
    print("头部控制成功")
except Exception as e:
    print(f"头部控制失败: {e}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")