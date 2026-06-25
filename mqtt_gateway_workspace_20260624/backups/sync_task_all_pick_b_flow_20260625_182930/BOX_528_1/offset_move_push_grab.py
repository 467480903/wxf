#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    _common = _parent / "mqtt_common"
    if _common.is_dir():
        sys.path.insert(0, str(_common))
        break

from mqtt_common import run_ee_offsets


def main() -> int:
    result_path = Path("/data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo/yolo_depth_result.json")
    if not result_path.exists():
        result_path = Path("/data/wxf/wxf/yolo/yolo_depth_result.json")
    with result_path.open("r", encoding="utf-8") as f:
        yolo_result = json.load(f)
    horizontal_offset_m = float(yolo_result["offset"]["horizontal_offset_px"]) / 1000.0
    run_ee_offsets(
        "BOX_528_1/offset_move_push_grab.py",
        offset_l=(0.0, horizontal_offset_m, 0.0),
        offset_r=(0.0, horizontal_offset_m, 0.0),
    )
    run_ee_offsets("BOX_528_1/offset_move_push_grab.py", offset_l=(0.09, 0.0, 0.0), offset_r=(0.09, 0.0, 0.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
