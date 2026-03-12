import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

slam = agibot_gdk.Slam()
time.sleep(2)  # 等待SLAM初始化

# 获取当前位姿
pose = slam.get_curr_pose()
print(f"当前位置: ({pose.position.x:.3f}, {pose.position.y:.3f}, {pose.position.z:.3f})")
print(f"当前方向: ({pose.orientation.x:.3f}, {pose.orientation.y:.3f}, {pose.orientation.z:.3f}, {pose.orientation.w:.3f})")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")