import agibot_gdk
import time
import json
import os

# 定义JSON文件路径
JSON_FILE_PATH = "/data/wxf/wxf/positions/arm_position_to_grab.json"

# ================= 1. 读取 JSON 配置文件 =================
print("正在读取目标位置配置...")
if not os.path.exists(JSON_FILE_PATH):
    print(f"❌ 找不到文件: {JSON_FILE_PATH}")
    exit(1)

try:
    with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
        pos_data = json.load(f)
    print("✅ JSON 配置读取成功")
except Exception as e:
    print(f"❌ 解析 JSON 文件失败: {e}")
    exit(1)

# ================= 2. 初始化 GDK 系统 =================
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("❌ GDK初始化失败")
    exit(1)
print("✅ GDK初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)  # 等待机器人初始化


# ================= 3. 提取手臂关节数据 =================
# 从字典中按顺序提取左臂 7 个关节数据（如果 JSON 里缺失某个键，默认给 0.0）
left_arm_pos = [
    pos_data.get("idx21_arm_l_joint1", 0.0),
    pos_data.get("idx22_arm_l_joint2", 0.0),
    pos_data.get("idx23_arm_l_joint3", 0.0),
    pos_data.get("idx24_arm_l_joint4", 0.0),
    pos_data.get("idx25_arm_l_joint5", 0.0),
    pos_data.get("idx26_arm_l_joint6", 0.0),
    pos_data.get("idx27_arm_l_joint7", 0.0)
]

# 按顺序提取右臂 7 个关节数据
right_arm_pos = [
    pos_data.get("idx61_arm_r_joint1", 0.0),
    pos_data.get("idx62_arm_r_joint2", 0.0),
    pos_data.get("idx63_arm_r_joint3", 0.0),
    pos_data.get("idx64_arm_r_joint4", 0.0),
    pos_data.get("idx65_arm_r_joint5", 0.0),
    pos_data.get("idx66_arm_r_joint6", 0.0),
    pos_data.get("idx67_arm_r_joint7", 0.0)
]

# 合并为机器人接口所需的 14 个关节数组
arm_positions = left_arm_pos + right_arm_pos

# 设定手臂运动的速度 (保持0.2弧度/秒)
arm_velocities = [0.2] * 14  # 简写形式：生成包含 14 个 0.2 的列表

# ================= 4. 执行运动控制 =================
try:
    print(f"准备发送手臂位置控制指令...")
    # 执行双臂关节运动
    result = robot.move_arm_joint(arm_positions, arm_velocities, 2)
    print("✅ 手臂控制成功")
except Exception as e:
    print(f"❌ 手臂控制失败: {e}")
    
# ================= 5. 释放系统资源 =================
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("❌ GDK释放失败")
else:
    print("✅ GDK释放成功")