import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

pnc = agibot_gdk.Pnc()
time.sleep(2)  # 等待PNC初始化

# 创建相对移动目标
target = agibot_gdk.NaviReq()
target.target.position.x = 0.0  # 相对前进0.5米
target.target.position.y = 0.5
target.target.position.z = 0.0
target.target.orientation.x = 0.0
target.target.orientation.y = 0.0
target.target.orientation.z = 0.0
target.target.orientation.w = 1.0
# agiNL0876
# 执行相对移动
try:
    pnc.relative_move(target)
    print("相对移动请求发送成功")
    time.sleep(2)
except Exception as e:
    print(f"相对移动失败: {e}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")