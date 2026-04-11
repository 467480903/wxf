import agibot_gdk
import time

def move_to_goal(pnc_handle, x, y, z, ox, oy, oz, ow):
    """封装导航请求发送函数"""
    target = agibot_gdk.NaviReq()
    target.target.position.x = x
    target.target.position.y = y
    target.target.position.z = z
    target.target.orientation.x = ox
    target.target.orientation.y = oy
    target.target.orientation.z = oz
    target.target.orientation.w = ow
    
    try:
        pnc_handle.normal_navi(target)
        print(f"目标点 ({x}, {y}) 导航请求发送成功")
        return True
    except Exception as e:
        print(f"导航失败: {e}")
        return False

# 1. 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

pnc = agibot_gdk.Pnc()
time.sleep(2)  # 等待PNC初始化

# --- 任务开始 ---

# 2. 前往第一个位置
# 位置: (-3.178, 0.713, 0.041), 方向: (-0.001, 0.006, -0.019, 1.000)
if move_to_goal(pnc, -3.178, 0.713, 0.041, -0.001, 0.006, -0.019, 1.000):
    print("正在前往第一个目标点...")
    # 注意：这里需要根据实际 SDK 提供的状态接口判断是否到达
    # 如果没有状态接口，简单的演示可以 sleep，但在生产环境中建议轮询里程计距离
    time.sleep(10)  # 假设需要 10 秒到达（请根据实际环境调整或替换为状态判断）

# 3. 前往第二个位置
# 位置: (11.460, 1.919, -0.023), 方向: (0.000, 0.001, 0.003, 1.000)
if move_to_goal(pnc, 11.460, 1.919, -0.023, 0.000, 0.001, 0.003, 1.000):
    print("正在前往第二个目标点...")
    time.sleep(10) 

# --- 任务结束 ---

# 4. 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")