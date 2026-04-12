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
# 数据来源：日志中的 idx21~idx27 (左臂) 和 idx61~idx67 (右臂) 的 位置(弧度)
arm_positions = [
    1.571, -1.571, -1.571, -1.571, 0.0, 0.0, 0.0,  # 左臂7个关节 (idx21_arm_l_joint1 ~ 7)
    -1.571, -1.571, 1.571, -1.571, 0.0, 0.0, 0.0   # 右臂7个关节 (idx61_arm_r_joint1 ~ 7)
]

# 设定手臂运动的速度 (保持0.3弧度/秒，确保机械臂有动力执行动作)
arm_velocities = [
    0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3,  # 左臂7个关节速度
    0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3   # 右臂7个关节速度
]

try:
    # 执行手臂关节运动
    result = robot.move_arm_joint(arm_positions, arm_velocities, 2)
    print("手臂控制成功")
except Exception as e:
    print(f"手臂控制失败: {e}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")