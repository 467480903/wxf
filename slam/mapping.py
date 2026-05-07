import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

# 初始化SLAM模块
slam = agibot_gdk.Slam()
time.sleep(2)  # 等待SLAM初始化

# 开始建图
try:
    slam.start_mapping()
    print("开始建图成功")
except Exception as e:
    print(f"开始建图失败: {e}")

# 建图过程中监控状态和位置
for i in range(10):
    try:
        odom_info = slam.get_odom_info()
        print(f"里程计位置: ({odom_info.pose.position.x:.3f}, {odom_info.pose.position.y:.3f}, {odom_info.pose.position.z:.3f})")
        print(f"里程计方向: ({odom_info.pose.orientation.x:.3f}, {odom_info.pose.orientation.y:.3f}, {odom_info.pose.orientation.z:.3f}, {odom_info.pose.orientation.w:.3f})")

        slam_state = slam.get_slam_state()
        print(f"SLAM状态: {slam_state}")

        pose = slam.get_curr_pose()
        print(f"当前位姿: ({pose.position.x:.3f}, {pose.position.y:.3f}, {pose.position.z:.3f})")

    except Exception as e:
        print(f"获取信息失败: {e}")

    time.sleep(1)

# 记录特定位置
try:
    slam.record_spec_loc()
    print("记录特定位置成功")
except Exception as e:
    print(f"记录特定位置失败: {e}")

# 停止建图
try:
    slam.stop_mapping()
    print("停止建图成功")
except Exception as e:
    print(f"停止建图失败: {e}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")