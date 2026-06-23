import os
import json
from offset_move_common import run_offset

RESULT_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yolo_depth_result.json")

with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
    result_data = json.load(f)
horizontal_offset_px = float(result_data["offset"]["horizontal_offset_px"])
print(f"从 yolo_depth_result.json 读取 offset/horizontal_offset_px = {horizontal_offset_px}")

if __name__ == "__main__":
    run_offset(offset_l=(0, horizontal_offset_px*(-0.2)/100 +0.02, 0), offset_r=(0, horizontal_offset_px*(-0.2)/100 +0.02, 0))
