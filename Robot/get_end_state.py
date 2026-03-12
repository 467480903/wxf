import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)  # 等待机器人初始化

# 获取末端执行器状态
end_state = robot.get_end_state()

# 打印左执行器状态
left_state = end_state['left_end_state']
print(f"左执行器控制状态: {left_state['controlled']}")
print(f"左执行器类型: {left_state['type']}")
print(f"左执行器关节: {left_state['names']}")

# 打印左执行器关节详细信息
for i, joint_state in enumerate(left_state['end_states']):
    print(f"\n左执行器关节 {i+1}:")
    print(f"  关节ID: {joint_state['id']}")
    print(f"  启用状态: {joint_state['enable']}")
    print(f"  位置: {joint_state['position']:.3f} 行程值")
    print(f"  速度: {joint_state['velocity']:.3f} 行程值/秒")
    print(f"  力矩: {joint_state['effort']:.3f} 牛顿·米")
    print(f"  电流: {joint_state['current']:.3f} 安培")
    print(f"  电压: {joint_state['voltage']:.3f} 伏特")
    print(f"  温度: {joint_state['temperature']:.1f} 摄氏度")
    print(f"  状态码: {joint_state['status']}")
    print(f"  错误码: {joint_state['err_code']}")

# 打印右执行器状态
right_state = end_state['right_end_state']
print(f"\n右执行器控制状态: {right_state['controlled']}")
print(f"右执行器类型: {right_state['type']}")
print(f"右执行器关节: {right_state['names']}")

# 检查执行器状态
print("\n=== 执行器状态检查 ===")
for side in ['left', 'right']:
    state = end_state[f'{side}_end_state']
    if state['controlled']:
        print(f"✅ {side}执行器正在控制中")
    else:
        print(f"❌ {side}执行器未控制")

    for joint_state in state['end_states']:
        if joint_state['err_code'] == 0:
            print(f"✅ {side}执行器关节{joint_state['id']}正常")
        else:
            print(f"❌ {side}执行器关节{joint_state['id']}错误码: {joint_state['err_code']}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")