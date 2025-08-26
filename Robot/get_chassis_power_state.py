import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)  # 等待机器人初始化

# 获取底盘电源状态
chassis_power_state = robot.get_chassis_power_state()
print(chassis_power_state)

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")