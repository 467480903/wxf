import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)  # 等待机器人初始化

# 获取全身状态
status = robot.get_whole_body_status()

# 打印基本信息
print(f"时间戳: {status['timestamp']}")
print(f"右执行器型号: {status['right_end_model']}")
print(f"左执行器型号: {status['left_end_model']}")

# 检查错误状态
print("\n=== 错误状态检查 ===")
if status['right_arm_error'] == 0:
    print("✅ 右臂正常")
else:
    print(f"❌ 右臂错误码: {status['right_arm_error']}")

if status['left_arm_error'] == 0:
    print("✅ 左臂正常")
else:
    print(f"❌ 左臂错误码: {status['left_arm_error']}")

if status['waist_error'] == 0:
    print("✅ 腰部正常")
else:
    print(f"❌ 腰部错误码: {status['waist_error']}")

if status['neck_error'] == 0:
    print("✅ 头部正常")
else:
    print(f"❌ 头部错误码: {status['neck_error']}")

if status['chassis_error'] == 0:
    print("✅ 底盘正常")
else:
    print(f"❌ 底盘错误码: {status['chassis_error']}")

# 检查控制状态
print("\n=== 控制状态 ===")
print(f"右臂控制: {'是' if status['right_arm_control'] else '否'}")
print(f"左臂控制: {'是' if status['left_arm_control'] else '否'}")
print(f"右臂急停: {'是' if status['right_arm_estop'] else '否'}")
print(f"左臂急停: {'是' if status['left_arm_estop'] else '否'}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")