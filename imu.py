import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

imu = agibot_gdk.Imu()
time.sleep(2)  # 等待IMU初始化

for i in range(10):
    # 获取最新IMU数据
    imu_data = imu.get_latest_imu(agibot_gdk.ImuType.kImuFront, 1000.0)

    if imu_data is not None:
        print(f"\n--- IMU数据 #{i+1} ---")
        print(f"时间戳: {imu_data.timestamp_ns}")

        # 角速度
        print(f"角速度: x={imu_data.angular_velocity.x:.4f}, "
              f"y={imu_data.angular_velocity.y:.4f}, "
              f"z={imu_data.angular_velocity.z:.4f}")
        # 线性加速度
        print(f"线性加速度: x={imu_data.linear_acceleration.x:.4f}, "
              f"y={imu_data.linear_acceleration.y:.4f}, "
              f"z={imu_data.linear_acceleration.z:.4f}")
    else:
        print(f"未收到IMU数据 #{i+1}")
    time.sleep(1.0)

# 关闭IMU
imu.close_imu()

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")