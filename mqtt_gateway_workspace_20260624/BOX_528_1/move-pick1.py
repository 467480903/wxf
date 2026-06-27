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


# Mirrors /data/wxf/wxf/BOX_528_1/move-pick1.py active lines:
#   robot.go_adjusted(2), robot.go(3)
# RobotController.go_adjusted(2) overwrites the map point position to
# x=0.2494, y=-0.3 and keeps the original waypoint-2 orientation. The
# gateway request-pose path needs yaw_rad instead of quaternion, so this yaw
# is derived from the current map waypoint-2 orientation seen in live logs.
WAYPOINTS = [
    {
        "source_waypoint_index": 2,
        "x_m": 0.2494,
        "y_m": -0.3,
        "yaw_rad": 1.6151929039873083,
        "high_precision": False,
        "note": "go_adjusted(2): adjusted pick approach point",
    },
    {"index": 3, "high_precision": False},
]


def main() -> int:
    run_nav_waypoints("BOX_528_1/move-pick1.py", WAYPOINTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
