
import agibot_gdk
import time

# 初始化 GDK 系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK 初始化失败")
    exit(1)
print("GDK 初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)  # 等待机器人初始化

# 获取运动控制状态
status = robot.get_motion_control_status()
print(f"运动模式: {status.mode}")
print(f"错误码: {status.error_code}")
print(f"错误信息: {status.error_msg}")
print(f"关节数量: {len(status.frame_names)}")
print(f"碰撞对数量: {len(status.collision_pairs_1)}")

# 打印所有关节名称
for i, frame_name in enumerate(status.frame_names):
    print(f"关节 {i}: {frame_name}")

# 释放 GDK 系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK 释放失败")
else:
    print("GDK 释放成功")