import agibot_gdk
import time

# 初始化 GDK 系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK 初始化失败")
    exit(1)
print("GDK 初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)  # 等待机器人初始化

# 创建末端执行器位姿控制请求
end_pose = agibot_gdk.EndEffectorPose()
end_pose.group = agibot_gdk.EndEffectorControlGroup.kBothArms
end_pose.left_end_effector_pose.position.x = 0.3
end_pose.left_end_effector_pose.position.y = 0.2
end_pose.left_end_effector_pose.position.z = 0.4
end_pose.right_end_effector_pose.position.x = 0.3
end_pose.right_end_effector_pose.position.y = -0.2
end_pose.right_end_effector_pose.position.z = 0.4
end_pose.life_time = 5.0

try:
    result = robot.end_effector_pose_control(end_pose)
    print("末端执行器位姿控制成功")
except Exception as e:
    print(f"末端执行器位姿控制失败: {e}")

# 释放 GDK 系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK 释放失败")
else:
    print("GDK 释放成功")