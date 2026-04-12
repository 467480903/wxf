import agibot_gdk
import time
import math

# 辅助函数：将四元数 (x, y, z, w) 转换为欧拉角 (Roll, Pitch, Yaw)
def quaternion_to_euler(x, y, z, w):
    """
    基于 ZYX 顺序将四元数转为欧拉角
    返回 (roll, pitch, yaw) 单位为弧度
    """
    # Roll (绕 X 轴旋转)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (绕 Y 轴旋转)
    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)  # 防止万向节死锁越界
    else:
        pitch = math.asin(sinp)

    # Yaw (绕 Z 轴旋转)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return roll, pitch, yaw


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

    print("=" * 60)
    print("当前末端位姿 (End-Effector Poses)")
    print("=" * 60)

    # 打印左手位姿
    if left_pose:
        r_l, p_l, y_l = quaternion_to_euler(left_pose.orientation.x, left_pose.orientation.y, 
                                            left_pose.orientation.z, left_pose.orientation.w)
        print("【左手】")
        print(f"  位置 [X, Y, Z]    : [{left_pose.position.x:.4f}, {left_pose.position.y:.4f}, {left_pose.position.z:.4f}]")
        print(f"  四元数 [X, Y, Z, W]: [{left_pose.orientation.x:.4f}, {left_pose.orientation.y:.4f}, {left_pose.orientation.z:.4f}, {left_pose.orientation.w:.4f}]")
        print(f"  欧拉角 (弧度)      : [Roll: {r_l:.4f}, Pitch: {p_l:.4f}, Yaw: {y_l:.4f}]")
        print(f"  欧拉角 (角度)      : [Roll: {math.degrees(r_l):.2f}°, Pitch: {math.degrees(p_l):.2f}°, Yaw: {math.degrees(y_l):.2f}°]\n")
    else:
        print(f"未找到左手末端帧: {left_link_name}\n")

    # 打印右手位姿
    if right_pose:
        r_r, p_r, y_r = quaternion_to_euler(right_pose.orientation.x, right_pose.orientation.y, 
                                            right_pose.orientation.z, right_pose.orientation.w)
        print("【右手】")
        print(f"  位置 [X, Y, Z]    : [{right_pose.position.x:.4f}, {right_pose.position.y:.4f}, {right_pose.position.z:.4f}]")
        print(f"  四元数 [X, Y, Z, W]: [{right_pose.orientation.x:.4f}, {right_pose.orientation.y:.4f}, {right_pose.orientation.z:.4f}, {right_pose.orientation.w:.4f}]")
        print(f"  欧拉角 (弧度)      : [Roll: {r_r:.4f}, Pitch: {p_r:.4f}, Yaw: {y_r:.4f}]")
        print(f"  欧拉角 (角度)      : [Roll: {math.degrees(r_r):.2f}°, Pitch: {math.degrees(p_r):.2f}°, Yaw: {math.degrees(y_r):.2f}°]\n")
    else:
        print(f"未找到右手末端帧: {right_link_name}\n")
        
    print("=" * 60)

except Exception as e:
    print(f"获取位姿失败: {e}")    

# 释放 GDK 系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK 释放失败")
else:
    print("GDK 释放成功")