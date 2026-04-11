import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

map_manager = agibot_gdk.Map()
time.sleep(2)  # 等待地图管理器初始化

# 获取当前地图
current_map = map_manager.get_curr_map()
print(f"当前地图:")
print(f"  地图ID: {current_map.id}")
print(f"  地图名称: {current_map.name}")
print(f"  是否为当前地图: {current_map.is_curr_map}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")