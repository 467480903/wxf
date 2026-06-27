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

from mqtt_common import run_nav_waypoints


# Mirrors /data/wxf/wxf/BOX_528_1/move-pick2.py:
#   robot.go(11), robot.go(14), robot.go(15), robot.go_adjusted(32)
# The original robot.go(13) is commented out and stays omitted.
WAYPOINTS = [
    {"index": 11, "high_precision": False},
    {"index": 14, "high_precision": False},
    {"index": 15, "high_precision": False},
    {
        "source_waypoint_index": 32,
        "x_m": 0.07965588715268747,
        "y_m": -0.6056166148205059,
        "yaw_rad": -1.5499916324135872,
        "high_precision": False,
        "note": "go_adjusted(32)",
    },
]


def main() -> int:
    run_nav_waypoints("BOX_528_1/move-pick2.py", WAYPOINTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
