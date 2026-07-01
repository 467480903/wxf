#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    _common = _parent / "mqtt_common"
    if _common.is_dir():
        sys.path.insert(0, str(_common))
        break

from mqtt_common import load_yolo_result_json, run_ee_offsets


def main() -> int:
    # Match the original calculation but read the freshest MQTT/original YOLO result.
    # _result_path, yolo_result = load_yolo_result_json("yolo_depth_result.json", base=Path(__file__).resolve().parents[1] / "yolo")
    # horizontal_offset_m = float(yolo_result["offset"]["horizontal_offset_px"]) / 1000.0
    # run_ee_offsets(
    #     "BOX_528_1/offset_move_push_grab.py",
    #     offset_l=(0.0, horizontal_offset_m, 0.0),
    #     offset_r=(0.0, horizontal_offset_m, 0.0),
    # )        controller.adjust_arms_relative(offset_l=(0.08+0.008, 0.04-0.006, 0  ), offset_r=(0.095+0.006, 0.03+0.008, 0))

    run_ee_offsets("BOX_528_1/offset_move_push_grab.py", offset_l=(0.088, 0.044, 0  ), offset_r=(0.099, 0.048, 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
