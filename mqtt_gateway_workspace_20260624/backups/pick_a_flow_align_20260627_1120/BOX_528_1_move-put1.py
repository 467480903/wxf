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


# Mirrors /data/wxf/wxf/BOX_528_1/move-put1.py active lines only:
#   robot.go(9), robot.go(10), robot.go_adjusted(12)
# The original robot.go(7), robot.go(8), and robot.go_adjusted(11) lines are
# commented out in the source script, so they must stay omitted here.
# The adjusted call is sent as an explicit map-frame target to preserve the
# original RobotController.go_adjusted coordinate edit.
WAYPOINTS = [
    {"index": 9, "high_precision": False},
    {"index": 10, "high_precision": False},
    {
        "source_waypoint_index": 12,
        "x_m": -1.0861968932515213,
        "y_m": -3.938110224686903,
        "yaw_rad": 0.0,
        "high_precision": False,
        "note": "go_adjusted(12)",
    },
]


def main() -> int:
    run_nav_waypoints("BOX_528_1/move-put1.py", WAYPOINTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
