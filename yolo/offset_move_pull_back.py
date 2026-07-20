import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ee_controller import EndEffectorController, init_gdk, release_gdk


def main():
    robot, _ = init_gdk()
    if robot is None:
        return

    try:
        controller = EndEffectorController(robot)
        controller.adjust_arms_relative(offset_l=(0, 0, 0.02), offset_r=(0, 0, 0.02))
        controller.adjust_arms_relative(offset_l=(-0.14, 0, 0), offset_r=(-0.14, 0,0))
    except Exception as e:
        print(f"[运行错误] {e}")

    release_gdk()


if __name__ == "__main__":
    main()
