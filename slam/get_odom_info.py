import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

slam = agibot_gdk.Slam()
time.sleep(2)  # 等待SLAM初始化

# 获取里程计信息
odom_info = slam.get_odom_info()
print(odom_info)
print(odom_info.pose.pose.position.x)
# linear_vel = odom_info.twist.linear
# print(odom_info.twist.linear)

# print("\n=== 查找包含 'linear' 的方法 ===")
# for attr in dir(odom_info.twist):
#     if 'linear' in attr.lower():
#         print(f"找到: {attr}")
#         try:
#             value = getattr(odom_info.twist, attr)
#             print(f"  值: {value}")
#         except:
#             print(f"  无法获取值")

print(f"位置: ({odom_info.pose.position.x:.3f}, {odom_info.pose.position.y:.3f}, {odom_info.pose.position.z:.3f})")
print(f"方向: ({odom_info.pose.orientation.x:.3f}, {odom_info.pose.orientation.y:.3f}, {odom_info.pose.orientation.z:.3f}, {odom_info.pose.orientation.w:.3f})")
print(f"线速度: ({odom_info.twist.linear.x:.3f}, {odom_info.twist.linear.y:.3f}, {odom_info.twist.linear.z:.3f})")
print(f"角速度: ({odom_info.twist.angular.x:.3f}, {odom_info.twist.angular.y:.3f}, {odom_info.twist.angular.z:.3f})")
print(f"是否静止: {odom_info.is_stationary}")
print(f"是否打滑: {odom_info.is_sliping}")
print(f"定位置信度: {odom_info.loc_confidence:.3f}")
print(f"定位状态: {odom_info.loc_state}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")