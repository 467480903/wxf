import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

lidar = agibot_gdk.Lidar()
time.sleep(2)  # 等待激光雷达初始化

pointcloud = lidar.get_latest_pointcloud(agibot_gdk.LidarType.kLidarFront, 1000.0)

if pointcloud is not None:
    print(f"✅ 时间戳: {pointcloud.timestamp_ns}")
    print(f"点云尺寸: {pointcloud.width} x {pointcloud.height}")
    print(f"点步长: {pointcloud.point_step}")
    print(f"行步长: {pointcloud.row_step}")
    print(f"是否大端序: {pointcloud.is_bigendian}")
    print(f"是否密集: {pointcloud.is_dense}")
    print(f"数据大小: {pointcloud.data_size} 字节")

    # 打印字段信息
    print(f"字段数量: {len(pointcloud.fields)}")
    for j, field in enumerate(pointcloud.fields):
        print(f"  字段 {j+1}: {field.name} (偏移: {field.offset}, "
              f"类型: {field.datatype}, 数量: {field.count})")
else:
    print("未获取到点云数据")

# 关闭激光雷达
lidar.close_lidar()

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")