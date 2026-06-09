#!/usr/bin/env python3
import sys, time
sys.path.insert(0, "/data/btgys/bengtian_backup_20260608_081250/wxf/BOX_528_1")
from chassis_controller import ChassisController

print("  [chassis] 初始化 GDK ...")
try:
    with ChassisController() as ctrl:
        # 先取消残留任务，清除可能的 motion_control_error
        print("  [chassis] 取消残留任务 ...")
        ctrl._cancel_blocking_task()
        time.sleep(0.5)

        print("  [chassis] 提交 relative_move(x=-1.5)  -- 后退 1.5m")
        state = ctrl.move_backward(1.5, timeout=30.0)
        print("  [chassis] relative_move 返回 state=" + str(state))

        # state: 3=成功, 7=已取消, 9=完成；-1=超时
        if state not in (3, 7, 9):
            print("  [chassis] ⚠️ 闭环未成功，改用开环速度控制后退")
            # vx<0 表示后退；按 0.25 m/s 预估时间
            vx = -0.25
            duration = abs(1.5) / abs(vx)
            print("  [chassis]   vx=" + str(vx) + " m/s, duration=" + str(round(duration,2)) + "s")
            ctrl.velocity_control(vx=vx, vy=0.0, vz=0.0, duration=duration, mode=1, hz=20)
            print("  [chassis]   开环控制完成")
        else:
            print("  [chassis] ✅ 闭环控制完成")
except Exception as e:
    print("  [chassis] ❌ 异常: " + str(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)
