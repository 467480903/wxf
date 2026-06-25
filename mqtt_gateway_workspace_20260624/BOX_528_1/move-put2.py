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


# Original /data/wxf/wxf/BOX_528_1/move-put2.py:
# go(19), go(20), go(21), go(22), go_adjusted(23), go_adjusted(25)
WAYPOINTS = [
    {"index": 19, "high_precision": False},
    {"index": 20, "high_precision": False},
    {"index": 21, "high_precision": False},
    {"index": 22, "high_precision": False},
    {"index": 23, "high_precision": True},
    {"index": 25, "high_precision": True},
]


def main() -> int:
    run_nav_waypoints("BOX_528_1/move-put2.py", WAYPOINTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
