import os
import json
from offset_move_common import run_offset

RESULT_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yolo_depth_result.json")

with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
    result_data = json.load(f)

point1_center_mm = float(result_data["depth"]["point1_center_mm"])
point2_center_mm = float(result_data["depth"]["point2_center_mm"])
print(f"从 yolo_depth_result.json 读取 depth/point1_center_mm = {point1_center_mm}, depth/point2_center_mm = {point2_center_mm}")

if point1_center_mm - point2_center_mm > 100:
    exit(1)
if point2_center_mm - point1_center_mm > 100:
    exit(1)

depth_offset = (point1_center_mm + point2_center_mm - 684 - 688) * 0.065 / (738 + 734 - 684 - 688)

if __name__ == "__main__":
    run_offset(offset_l=(depth_offset, 0, 0), offset_r=(depth_offset, 0, 0))
