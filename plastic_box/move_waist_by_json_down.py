import agibot_gdk
import time
import json
import os

# 定义JSON文件路径
JSON_FILE_PATH = "/data/wxf/wxf_421/positions/positions_plastic_box_pick_down.json"

# ================= 1. 读取 JSON 配置文件 =================
print("正在读取腰部目标位置配置...")
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

# ================= 3. 提取腰部关节数据 =================
# 从字典中按顺序提取腰部 5 个关节数据（如果 JSON 里缺失某个键，默认给 0.0）
waist_positions = [
    pos_data.get("idx01_body_joint1", 0.0),
    pos_data.get("idx02_body_joint2", 0.0),
    pos_data.get("idx03_body_joint3", 0.0),
    pos_data.get("idx04_body_joint4", 0.0),
    pos_data.get("idx05_body_joint5", 0.0)
]

# 设定腰部运动的速度 (保持0.3弧度/秒)
waist_velocities = [0.3, 0.3, 0.3, 0.3, 0.3] 

# ================= 4. 执行运动控制 =================
try:
    print(f"准备发送腰部位置控制指令: {waist_positions}")
    result = robot.move_waist_joint(waist_positions, waist_velocities)
    print("✅ 腰部控制成功")
except Exception as e:
    print(f"❌ 腰部控制失败: {e}")

# ================= 5. 释放系统资源 =================
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("❌ GDK释放失败")
else:
    print("✅ GDK释放成功")