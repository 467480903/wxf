
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
    
# 定义我们要寻找的末端连杆名称
left_link_name = "arm_l_end_link"
right_link_name = "arm_r_end_link"

try:
    # 获取机器人当前的完整运动控制状态
    status = robot.get_motion_control_status()
    
    left_pose = None
    right_pose = None

    # 遍历所有的 frame，匹配左右手末端的名字
    for i, frame_name in enumerate(status.frame_names):
        if frame_name == left_link_name:
            left_pose = status.frame_poses[i]
        elif frame_name == right_link_name:
            right_pose = status.frame_poses[i]

    print("=" * 40)
    print("当前末端位姿 (End-Effector Poses)")
    print("=" * 40)

    # 打印左手位姿
    if left_pose:
        print("【左手】")
        print(f"  位置 [X, Y, Z] : [{left_pose.position.x:.4f}, {left_pose.position.y:.4f}, {left_pose.position.z:.4f}]")
        print(f"  姿态 [X, Y, Z, W]: [{left_pose.orientation.x:.4f}, {left_pose.orientation.y:.4f}, {left_pose.orientation.z:.4f}, {left_pose.orientation.w:.4f}]\n")
    else:
        print(f"未找到左手末端帧: {left_link_name}\n")

    # 打印右手位姿
    if right_pose:
        print("【右手】")
        print(f"  位置 [X, Y, Z] : [{right_pose.position.x:.4f}, {right_pose.position.y:.4f}, {right_pose.position.z:.4f}]")
        print(f"  姿态 [X, Y, Z, W]: [{right_pose.orientation.x:.4f}, {right_pose.orientation.y:.4f}, {right_pose.orientation.z:.4f}, {right_pose.orientation.w:.4f}]\n")
    else:
        print(f"未找到右手末端帧: {right_link_name}\n")
        
    print("=" * 40)

except Exception as e:
    print(f"获取位姿失败: {e}")    

# 释放 GDK 系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK 释放失败")
else:
    print("GDK 释放成功")