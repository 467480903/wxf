import agibot_gdk

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

camera = agibot_gdk.Camera()

intrinsic = camera.get_camera_intrinsic(agibot_gdk.CameraType.kHeadStereoLeft)
print(f"相机内参:")
print(f"  fx: {intrinsic.intrinsic[0]}")
print(f"  fy: {intrinsic.intrinsic[1]}")
print(f"  cx: {intrinsic.intrinsic[2]}")
print(f"  cy: {intrinsic.intrinsic[3]}")

print(f"畸变参数:")
for i, dist in enumerate(intrinsic.distortion):
    print(f"  k{i+1}: {dist}")

# 关闭相机
camera.close_camera()

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")