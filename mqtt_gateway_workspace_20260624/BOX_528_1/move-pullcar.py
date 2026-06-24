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


WAYPOINTS = [{'index': 26, 'high_precision': False}, {'index': 27, 'high_precision': False}, {'index': 28, 'high_precision': False}, {'index': 29, 'high_precision': False}, {'index': 30, 'high_precision': False}, {'index': 31, 'high_precision': False}]


def main() -> int:
    run_nav_waypoints("BOX_528_1/move_pullcar.py", WAYPOINTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
