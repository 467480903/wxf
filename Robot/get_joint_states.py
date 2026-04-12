import agibot_gdk
import time
import json  # 引入 json 模块

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

# 准备一个字典来收集我们要保存的位置数据
positions_dict = {}

for state in joint_states['states']:
    print(f"关节: {state['name']}")
    print(f"  位置: {state['position']:.3f} 弧度")
    print(f"  速度: {state['velocity']:.3f} 弧度/秒")
    print(f"  力矩: {state['effort']:.3f} 牛顿·米")
    print(f"  电机位置: {state['motor_position']:.3f} 弧度")
    print(f"  电机电流: {state['motor_current']:.3f} 安培")
    print(f"  错误码: {state['error_code']}")
    
    # 将关节名称作为键，位置(保留3位小数)作为值，存入字典
    positions_dict[state['name']] = round(state['position'], 3)

# 将提取到的关节位置数据保存为 JSON 文件
try:
    with open("positions.json", "w", encoding="utf-8") as f:
        # indent=4 让生成的 JSON 文件带缩进，人类可读性更好
        json.dump(positions_dict, f, ensure_ascii=False, indent=4)
    print("\n✅ 所有关节角度已成功保存到 positions.json 中\n")
except Exception as e:
    print(f"\n❌ 保存 JSON 文件失败: {e}\n")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")