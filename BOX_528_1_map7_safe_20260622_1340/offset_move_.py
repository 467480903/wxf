import agibot_gdk
import time
from end_effector_controller import EndEffectorController


# ═══════════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════════

def main():
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK 初始化失败")
        return
    print("GDK 初始化成功")

    robot = agibot_gdk.Robot()
    time.sleep(2)   # 等待机器人就绪

    try:
        controller = EndEffectorController(robot)
        
        # ───────────────────────────────────────────────────────
        # 使用说明：
        # offset 参数格式为 (X偏移, Y偏移, Z偏移)，单位为 米。
        # 坐标系规则： X+(向前)， Y+(向左)， Z+(向上)
        # ───────────────────────────────────────────────────────

        controller.adjust_arms_relative(offset_l=(-0.10, 0, 0), offset_r=(-0.10, 0, 0))#后缩
        # controller.adjust_arms_relative(offset_l=(-0.005, 0, 0), offset_r=(0, 0, 0))#前伸

    except Exception as e:
        print(f"[运行错误] {e}")

    # 释放GDK系统资源
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("GDK释放失败")
    else:
        print("GDK释放成功")

if __name__ == "__main__":
    main()