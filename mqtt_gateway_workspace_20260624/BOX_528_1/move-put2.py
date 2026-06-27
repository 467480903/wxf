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


# Mirrors /data/wxf/wxf/BOX_528_1/move-put2.py:
#   robot.go(22), robot.go_adjusted(23), robot.go_adjusted(25)
# The original go(19), go(20), and go(21) lines are commented out and stay
# omitted. The adjusted targets are sent as explicit map-frame poses.
WAYPOINTS = [
    {"index": 22, "high_precision": False},
    {
        "source_waypoint_index": 23,
        "x_m": 1.4891060183247533,
        "y_m": -3.9044867812030795,
        "yaw_rad": 3.1155985098813317,
        "high_precision": False,
        "note": "go_adjusted(23)",
    },
    {
        "source_waypoint_index": 25,
        "x_m": 1.3796321001429732,
        "y_m": -3.9044867812030795,
        "yaw_rad": 3.1155985098813317,
        "high_precision": False,
        "note": "go_adjusted(25)",
    },
]


def main() -> int:
    run_nav_waypoints("BOX_528_1/move-put2.py", WAYPOINTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
