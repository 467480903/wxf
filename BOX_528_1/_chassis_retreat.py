#!/usr/bin/env python3
import sys, time
import agibot_gdk

print("  [retreat] 初始化 GDK ...")
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("  [retreat] ❌ GDK 初始化失败")
    sys.exit(1)

pnc = agibot_gdk.Pnc()
robot = agibot_gdk.Robot()
time.sleep(1.0)  # 等待 DDS 连接建立

# 1. 查看当前底盘状态（带重试）
for attempt in range(5):
    try:
        motion = robot.get_motion_control_status()
        print("  [retreat] 当前 motion_control_error=" + str(getattr(motion, "error_code", "N/A")))
        break
    except Exception as e:
        print("  [retreat] 读取状态失败(" + str(attempt+1) + "/5): " + str(e))
        time.sleep(1.0)

# 2. 取消残留 PNC 任务
for attempt in range(3):
    try:
        task = pnc.get_task_state()
        print("  [retreat] 当前 task state=" + str(task.state) + " id=" + str(task.id))
        if task.state not in (0, 3, 7, 9):
            print("  [retreat] 取消残留任务 ...")
            pnc.cancel_task(task.id)
            time.sleep(0.5)
        break
    except Exception as e:
        print("  [retreat] 获取任务状态失败(" + str(attempt+1) + "/3): " + str(e))
        time.sleep(1.0)

# 3. 请求底盘远控（mode=0，与 dock 一致），这会清除 motion_control_error
print("  [retreat] 请求底盘远控 ...")
for attempt in range(3):
    try:
        pnc.request_chassis_control(0)
        print("  [retreat] 底盘远控申请成功")
        break
    except Exception as e:
        print("  [retreat] 底盘远控申请失败(" + str(attempt+1) + "/3): " + str(e))
        time.sleep(1.0)

time.sleep(0.5)

# 4. 发零速，确认底盘可控
twist = agibot_gdk.Twist()
twist.linear = agibot_gdk.Vector3()
twist.angular = agibot_gdk.Vector3()
twist.linear.x = 0.0
twist.linear.y = 0.0
twist.angular.z = 0.0
try:
    pnc.move_chassis(twist)
    print("  [retreat] 零速发送成功")
except Exception as e:
    print("  [retreat] 零速发送失败: " + str(e))
time.sleep(0.5)

# 5. 确认 motion_control_error 已清除
try:
    motion = robot.get_motion_control_status()
    print("  [retreat] 重置后 motion_control_error=" + str(getattr(motion, "error_code", "N/A")))
except Exception as e:
    print("  [retreat] 无法读取状态（不影响后退）: " + str(e))

# 6. 开始后退：vx < 0，0.25 m/s
vx = -0.25
duration = 1.4 / abs(vx)
print("  [retreat] 开始后退 vx=" + str(vx) + " m/s, duration=" + str(round(duration, 2)) + "s")

twist.linear.x = vx
start = time.time()
hz = 20
interval = 1.0 / hz
while time.time() - start < duration:
    try:
        pnc.move_chassis(twist)
    except Exception as e:
        print("  [retreat] 发速异常: " + str(e))
    time.sleep(interval)

# 7. 停车
twist.linear.x = 0.0
try:
    pnc.move_chassis(twist)
except Exception:
    pass
print("  [retreat] ✅ 后退完成")

time.sleep(0.3)
agibot_gdk.gdk_release()
