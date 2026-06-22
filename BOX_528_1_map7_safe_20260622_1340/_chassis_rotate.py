#!/usr/bin/env python3
import sys, time, math
import agibot_gdk

print("  [rotate] 初始化 GDK ...")
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("  [rotate] ❌ GDK 初始化失败")
    sys.exit(1)

pnc = agibot_gdk.Pnc()
time.sleep(1.0)  # 等待 DDS 连接建立

# 1. 取消残留 PNC 任务（带重试）
for attempt in range(3):
    try:
        task = pnc.get_task_state()
        if task.state not in (0, 3, 7, 9):
            print("  [rotate] 取消残留任务 state=" + str(task.state))
            pnc.cancel_task(task.id)
            time.sleep(0.5)
        break
    except Exception as e:
        print("  [rotate] 获取任务状态失败(" + str(attempt+1) + "/3): " + str(e))
        time.sleep(1.0)

# 2. 请求底盘远控（带重试）
print("  [rotate] 请求底盘远控 ...")
for attempt in range(3):
    try:
        pnc.request_chassis_control(0)
        print("  [rotate] 底盘远控申请成功")
        break
    except Exception as e:
        print("  [rotate] 远控申请失败(" + str(attempt+1) + "/3): " + str(e))
        time.sleep(1.0)
time.sleep(0.5)

# 3. 发零速确认可控
twist = agibot_gdk.Twist()
twist.linear = agibot_gdk.Vector3()
twist.angular = agibot_gdk.Vector3()
try:
    pnc.move_chassis(twist)
    print("  [rotate] 零速发送成功")
except Exception as e:
    print("  [rotate] 零速发送失败: " + str(e))
time.sleep(0.5)

# 4. 旋转
vz_rad = math.radians(30.0)  # ~30 deg/s
if 90 < 0:
    vz_rad = -vz_rad
duration = abs(90) / 30.0
print("  [rotate] 旋转 90° vz=" + str(round(vz_rad, 3)) + " rad/s, duration=" + str(round(duration, 2)) + "s")

twist.angular.z = vz_rad
start = time.time()
hz = 20
interval = 1.0 / hz
while time.time() - start < duration:
    try:
        pnc.move_chassis(twist)
    except Exception as e:
        print("  [rotate] 发速异常: " + str(e))
    time.sleep(interval)

# 5. 停车
twist.angular.z = 0.0
try:
    pnc.move_chassis(twist)
except Exception:
    pass
print("  [rotate] ✅ 旋转完成")

time.sleep(0.3)
agibot_gdk.gdk_release()
