import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

pnc = agibot_gdk.Pnc()
time.sleep(2)  # 等待PNC初始化

# 获取任务状态
task_state = pnc.get_task_state()
print(f"PNC任务状态: {task_state.state}")
print(f"PNC任务ID: {task_state.id}")
print(f"PNC任务内容: {task_state.message}")
print(f"PNC任务种类: {task_state.type}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")