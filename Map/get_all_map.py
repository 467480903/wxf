import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

map_manager = agibot_gdk.Map()
time.sleep(2)  # 等待地图管理器初始化

# 获取所有地图
all_maps = map_manager.get_all_map()
print(f"所有地图数量: {len(all_maps)}")

for i, map_name in enumerate(all_maps):
    print(f"地图 {i+1}:")
    print(f"  ID: {map_name.id}")
    print(f"  名称: {map_name.name}")
    print(f"  是否为当前地图: {map_name.is_curr_map}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")