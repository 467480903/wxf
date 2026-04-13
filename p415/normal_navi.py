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




diff = 0 # 可以根据需要调整位置偏移量
# 创建导航目标
target = agibot_gdk.NaviReq()
target.target.position.x = -1.850+diff
target.target.position.y = 0.609+diff
target.target.position.z = -0.010
target.target.orientation.x = -0.001
target.target.orientation.y = -0.007
target.target.orientation.z = -0.255
target.target.orientation.w = 0.967



# 执行导航
try:
    pnc.normal_navi(target)
    # pnc.MoveChassis(target)
    print("正常导航请求发送成功")
except Exception as e:
    print(f"正常导航失败: {e}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")