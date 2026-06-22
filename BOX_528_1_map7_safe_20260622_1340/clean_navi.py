import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

pnc = agibot_gdk.Pnc()
time.sleep(2)  # 等待PNC初始化

# 先获取当前任务状态以获取任务ID
try:
    task_state = pnc.get_task_state()
    task_id = task_state.id

    # 取消指定ID的导航任务
    pnc.cancel_task(task_id)
    print("取消任务请求发送成功")
    time.sleep(1)  # 等待任务取消完成
except Exception as e:
    print(f"取消任务失败: {e}")




