import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ee_controller import EndEffectorController, init_gdk, release_gdk

HOLES_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "holes_result.json")
HANDS_PICK_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hands_pick_result.json")


def load_h_offset(path):
    if not os.path.exists(path):
        print(f"❌ 找不到 {path}")
        return None
    with open(path, 'r') as f:
        data = json.load(f)
    return data['h_offset']


def main():
    h_offset_holes = load_h_offset(HOLES_JSON)
    h_offset_hands = load_h_offset(HANDS_PICK_JSON)

    if h_offset_holes is None or h_offset_hands is None:
        print("❌ 缺少必要的 JSON 数据，退出")
        return

    offset_px = (h_offset_holes - h_offset_hands) / 2.0
    print(f"holes h_offset: {h_offset_holes:.2f} px")
    print(f"hands_pick h_offset: {h_offset_hands:.2f} px")
    print(f"最终水平偏移量: ({h_offset_holes:.2f} - {h_offset_hands:.2f}) / 2 = {offset_px:.2f} px")

    offset_m = offset_px * 0.001
    print(f"换算为米 (1px ≈ 1mm): {offset_m:.6f} m")

    robot, _ = init_gdk()
    if robot is None:
        return

    try:
        controller = EndEffectorController(robot)
        controller.adjust_arms_relative(offset_l=(offset_m, 0, 0), offset_r=(offset_m, 0, 0))
    except Exception as e:
        print(f"[运行错误] {e}")

    release_gdk()


if __name__ == "__main__":
    main()
