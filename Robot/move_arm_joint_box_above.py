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
arm_positions = [1.369, -1.651, -1.281, -1.796, 1.994, 0.316, -1.502,  # 左臂7个关节
                 -1.344, -1.327, 1.348, -1.753, -1.358, 0.141, 1.082]  # 右臂7个关节
arm_velocities = [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2,  # 左臂7个关节速度
                  0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]  # 右臂7个关节速度

try:
    result = robot.move_arm_joint(arm_positions, arm_velocities,2)
    print("手臂控制成功")
except Exception as e:
    print(f"手臂控制失败: {e}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")