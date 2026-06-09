#!/usr/bin/env python3
"""
总控程序：按指定顺序执行 18 个动作
所有动作都以独立子进程执行，避免 GDK init/release 状态冲突
运行方式：
  cd /data/btgys/bengtian_backup_20260608_081250/wxf/BOX_528_1
  python3 main_controller.py
"""

import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

PYTHON = sys.executable


# ======================================================================
# 核心：统一以独立子进程方式执行每一步，每个子进程自己管理 gdk_init/release
# ======================================================================
def _run_subprocess(cwd, args, step_label):
    """
    以子进程方式执行一条命令，阻塞等待完成。
    返回 returncode。子进程 stdout/stderr 直接转发到终端。
    """
    print("\n" + "=" * 60)
    print(f"[{step_label}]")
    print(f"  命令: {' '.join(args)}")
    print("=" * 60)
    result = subprocess.run(args, cwd=cwd)
    if result.returncode != 0:
        print(f"  ⚠️  返回码={result.returncode}，继续执行下一步")
    print()
    return result.returncode


def _run_script_file(script_path, cwd, step_label, extra_args=None):
    """执行一个 .py 脚本文件（比 python -c 更稳定）。"""
    args = [PYTHON, script_path]
    if extra_args:
        args.extend(extra_args)
    return _run_subprocess(cwd, args, step_label)


def run_py_script(script_name, step_label):
    """运行当前目录下的一个 Python 脚本。"""
    script_abs = os.path.join(SCRIPT_DIR, script_name)
    return _run_script_file(script_abs, SCRIPT_DIR, step_label)


def dock_execute(final_stop_mm, step_label):
    """
    运行 rack_hybrid_docking_demo.py --execute，目标距离 final_stop_mm。
    直接 execute，不需要手动选模式。
    """
    script = os.path.join(SCRIPT_DIR, "rack_hybrid_docking_package", "rack_hybrid_docking_demo.py")
    pkg_dir = os.path.join(SCRIPT_DIR, "rack_hybrid_docking_package")
    return _run_subprocess(
        pkg_dir,
        [
            PYTHON, script,
            "--execute",
            "--allow-estop-pedal-fault",
            f"--final-stop-mm={final_stop_mm}",
        ],
        step_label,
    )


def dock_retreat(distance_m, step_label):
    """
    底盘后退 distance_m 米。
    先重置底盘状态（清除 dock 后残留的 motion_control_error），
    再用 velocity_control 开环后退。
    """
    body = f'''#!/usr/bin/env python3
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
duration = {distance_m} / abs(vx)
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
'''
    script = _write_chassis_script("_chassis_retreat.py", body)
    return _run_script_file(script, SCRIPT_DIR, step_label)


# ======================================================================
# 底盘动作：每次生成一个独立的 .py 临时文件并执行
# 每一次底盘动作都在一个干净的进程里完成 ChassisController 的 init/release
# 关键修复：
#   1. 用 .py 文件代替 python -c，避免 shell/字符串解析问题
#   2. 加 try/except 捕获 GDK init、relative_move 的所有异常
#   3. 打印任务 state 的实时变化，便于定位"不动"的原因
#   4. relative_move 失败时再试一次 velocity_control（开环）作为 fallback
# ======================================================================

def _write_chassis_script(script_name, body):
    """在 SCRIPT_DIR 下写一个临时 .py 文件，返回绝对路径。"""
    path = os.path.join(SCRIPT_DIR, script_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def chassis_move_backward(distance_m, step_label):
    """
    底盘后退 distance_m 米。
    先尝试 relative_move（闭环）；若 state 非成功状态，再回退到
    velocity_control 开环速度控制，确保机器人至少会动。
    """
    body = f'''#!/usr/bin/env python3
import sys, time
sys.path.insert(0, "{SCRIPT_DIR}")
from chassis_controller import ChassisController

print("  [chassis] 初始化 GDK ...")
try:
    with ChassisController() as ctrl:
        # 先取消残留任务，清除可能的 motion_control_error
        print("  [chassis] 取消残留任务 ...")
        ctrl._cancel_blocking_task()
        time.sleep(0.5)

        print("  [chassis] 提交 relative_move(x=-{distance_m})  -- 后退 {distance_m}m")
        state = ctrl.move_backward({distance_m}, timeout=30.0)
        print("  [chassis] relative_move 返回 state=" + str(state))

        # state: 3=成功, 7=已取消, 9=完成；-1=超时
        if state not in (3, 7, 9):
            print("  [chassis] ⚠️ 闭环未成功，改用开环速度控制后退")
            # vx<0 表示后退；按 0.25 m/s 预估时间
            vx = -0.25
            duration = abs({distance_m}) / abs(vx)
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
'''
    script = _write_chassis_script("_chassis_backward.py", body)
    return _run_script_file(script, SCRIPT_DIR, step_label)


def chassis_rotate(angle_deg, step_label):
    """
    底盘原地旋转 angle_deg 度。正值=逆时针，负值=顺时针。
    先重置底盘状态，再用 velocity_control 开环旋转。
    """
    body = f'''#!/usr/bin/env python3
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
if {angle_deg} < 0:
    vz_rad = -vz_rad
duration = abs({angle_deg}) / 30.0
print("  [rotate] 旋转 {angle_deg}° vz=" + str(round(vz_rad, 3)) + " rad/s, duration=" + str(round(duration, 2)) + "s")

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
'''
    script = _write_chassis_script("_chassis_rotate.py", body)
    return _run_script_file(script, SCRIPT_DIR, step_label)


# ======================================================================
# 主流程：18 步
# ======================================================================
def main():
    steps = [
        ("① /18  打开夹爪",
         lambda: run_py_script("move_ee_pose_open_2.py", "① open gripper")),

        ("② /18  手臂移动到第一根位置",
         lambda: run_py_script("move_arm_magnet_第一根.py", "② arm → 第一根")),

        ("③ /18  用前雷达向前靠近到 540mm",
         lambda: dock_execute(550, "③ dock → 540mm")),

        ("④ /18  手臂向下偏移 50mm",
         lambda: run_py_script("offset_move_down.py", "④ arm down")),

        ("⑤ /18  闭合夹爪",
         lambda: run_py_script("move_ee_pose_close_2.py", "⑤ close gripper")),

        ("⑥ /18  手臂向上偏移 50mm",
         lambda: run_py_script("offset_move_up.py", "⑥ arm up")),

        ("⑦ /18  手臂向后拉 150mm",
         lambda: run_py_script("offset_move_pull.py", "⑦ arm pull")),

        ("⑧ /18  底盘后退 1.5 米（retreat）",
         lambda: dock_retreat(1.4, "⑧ retreat 1.5m")),

        ("⑨ /18  底盘向右转 90 度（顺时针）",
         lambda: chassis_rotate(-90, "⑨ chassis rotate -90°")),

        ("⑩ /18  手臂移动到送料位置",
         lambda: run_py_script("move_arm_magnet_送.py", "⑩ arm → 送")),

        ("⑪ /18  用前雷达向前靠近到 610mm",
         lambda: dock_execute(630, "⑪ dock → 620mm")),

        ("⑫ /18  手臂向下偏移 50mm",
         lambda: run_py_script("offset_move_down.py", "⑫ arm down")),

        ("⑬ /18  打开夹爪",
         lambda: run_py_script("move_ee_pose_open_2.py", "⑬ open gripper")),

        ("⑭ /18  手臂向上偏移 50mm",
         lambda: run_py_script("offset_move_up.py", "⑭ arm up")),

        ("⑮ /18  手臂向后拉 150mm",
         lambda: run_py_script("offset_move_pull.py", "⑮ arm pull")),

        ("⑯ /18  底盘后退 1.5 米（retreat）",
         lambda: dock_retreat(1.4, "⑯ retreat 1.5m")),

        ("⑰ /18  底盘向左转 90 度（逆时针）",
         lambda: chassis_rotate(90, "⑰ chassis rotate +90°")),

        ("⑱ /18  手臂移动回第一根位置",
         lambda: run_py_script("move_arm_magnet_第一根.py", "⑱ arm → 第一根")),
    ]

    print("=" * 60)
    print("  总控程序启动")
    print(f"  脚本目录: {SCRIPT_DIR}")
    print(f"  共 {len(steps)} 个步骤，全部以独立子进程方式执行")
    print("=" * 60)

    failed = []
    for idx, (description, action) in enumerate(steps, 1):
        print(f"\n━━━━ 步骤 {idx}/{len(steps)}: {description} ━━━━")
        try:
            rc = action()
            if rc != 0:
                failed.append((idx, description, f"returncode={rc}"))
        except Exception as e:
            print(f"  ❌ 步骤异常: {e}")
            failed.append((idx, description, str(e)))

    print("\n" + "=" * 60)
    if failed:
        print(f"  执行完毕，共 {len(failed)} 个步骤返回非零或异常：")
        for idx, desc, err in failed:
            print(f"    [{idx:>2}] {desc}  → {err}")
    else:
        print("  所有 18 个步骤执行完毕")
    print("=" * 60)


if __name__ == "__main__":
    main()
