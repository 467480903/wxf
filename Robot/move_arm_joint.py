import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)  # 等待机器人初始化

# 控制手臂位置（按照关节顺序：左臂7个关节 + 右臂7个关节）
arm_positions = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,  # 左臂7个关节
                 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # 右臂7个关节
arm_velocities = [0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3,  # 左臂7个关节速度
                  0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3]  # 右臂7个关节速度

try:
    result = robot.move_arm_joint(arm_positions, arm_velocities)
    print("手臂控制成功")
except Exception as e:
    print(f"手臂控制失败: {e}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")