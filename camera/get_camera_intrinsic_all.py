import agibot_gdk

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

camera = agibot_gdk.Camera()

# 定义所有相机类型列表
camera_types = [
    (agibot_gdk.CameraType.kHeadBackFisheye, "头部背部鱼眼相机"),
    (agibot_gdk.CameraType.kHeadLeftFisheye, "头部左侧鱼眼相机"),
    (agibot_gdk.CameraType.kHeadRightFisheye, "头部右侧鱼眼相机"),
    (agibot_gdk.CameraType.kHeadStereoLeft, "头部立体左相机"),
    (agibot_gdk.CameraType.kHeadStereoRight, "头部立体右相机"),
    (agibot_gdk.CameraType.kHandLeftColor, "左手彩色相机"),
    (agibot_gdk.CameraType.kHandRightColor, "右手彩色相机"),
    (agibot_gdk.CameraType.kHeadColor, "头部彩色相机"),
    (agibot_gdk.CameraType.kHeadDepth, "头部深度相机"),
    (agibot_gdk.CameraType.kHandLeftDepth, "左手深度相机"),
    (agibot_gdk.CameraType.kHandRightDepth, "右手深度相机"),
    (agibot_gdk.CameraType.kHandLeftUpperColor, "左手上部彩色相机"),
    (agibot_gdk.CameraType.kHandRightUpperColor, "右手上部彩色相机"),
    (agibot_gdk.CameraType.kHandLeftLowerColor, "左手下部彩色相机"),
    (agibot_gdk.CameraType.kHandRightLowerColor, "右手下部彩色相机"),
    (agibot_gdk.CameraType.kHandLeftUpperDepth, "左手上部深度相机"),
    (agibot_gdk.CameraType.kHandRightUpperDepth, "右手上部深度相机"),
    (agibot_gdk.CameraType.kHandLeftLowerDepth, "左手下部深度相机"),
    (agibot_gdk.CameraType.kHandRightLowerDepth, "右手下部深度相机")
]

print("开始获取所有相机参数...\n")

for camera_type, type_name in camera_types:
    try:
        print(f"=== {type_name} ===")
        
        # 获取相机内参
        intrinsic = camera.get_camera_intrinsic(camera_type)
        
        print(f"相机内参:")
        print(f"  fx: {intrinsic.intrinsic[0]}")
        print(f"  fy: {intrinsic.intrinsic[1]}")
        print(f"  cx: {intrinsic.intrinsic[2]}")
        print(f"  cy: {intrinsic.intrinsic[3]}")
        
        print(f"畸变参数:")
        # 假设distortion是一个列表，包含畸变系数
        for i, dist in enumerate(intrinsic.distortion):
            print(f"  k{i+1}: {dist}")
        
        print()  # 添加空行分隔不同的相机
        
    except Exception as e:
        print(f"获取 {type_name} 参数失败: {e}\n")

# 关闭相机
camera.close_camera()

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")