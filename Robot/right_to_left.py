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
arm_positions = [
    # 左臂7个关节 (从日志提取)
    0.753, -1.710, -1.004, -0.522, 1.052, 0.574, -0.627,  
    # 右臂7个关节 (依据左臂数据进行对称计算：关节4、6相同，其余乘 -1)
    -0.753, -1.710, 1.004, -0.522, -1.052, 0.574, 0.627    
]

arm_positions2 = [
    # 左臂7个关节 (从日志提取)
    0.749 , -1.578, -0.986, -0.582, 1.070,  0.253, -0.955,
    # 右臂7个关节 (依据左臂数据进行对称计算：关节4、6相同，其余乘 -1)
    -0.749 , -1.578, 0.986, -0.582, -1.070,  0.253, 0.955
]

# 设定手臂运动的速度 (保持0.2弧度/秒)
arm_velocities = [
    0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2,  # 左臂7个关节速度
    0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2   # 右臂7个关节速度
]

try:
    # 执行双臂关节运动
    result = robot.move_arm_joint(arm_positions2, arm_velocities, 2)
    print("手臂控制成功")
except Exception as e:
    print(f"手臂控制失败: {e}")
    
# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")