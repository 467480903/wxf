import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)  # 等待机器人初始化

# 获取关节状态
joint_states = robot.get_joint_states()
print(f"关节数量: {joint_states['nums']}")
print(f"时间戳: {joint_states['timestamp']}")

for state in joint_states['states']:
    print(f"关节: {state['name']}")
    print(f"  位置: {state['position']:.3f} 弧度")
    print(f"  速度: {state['velocity']:.3f} 弧度/秒")
    print(f"  力矩: {state['effort']:.3f} 牛顿·米")
    print(f"  电机位置: {state['motor_position']:.3f} 弧度")
    print(f"  电机电流: {state['motor_current']:.3f} 安培")
    print(f"  错误码: {state['error_code']}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")