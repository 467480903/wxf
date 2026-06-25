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


WAYPOINTS = [{'index': 11, 'high_precision': False}, {'index': 13, 'high_precision': False}, {'index': 14, 'high_precision': False}, {'index': 15, 'high_precision': False}, {'index': 17, 'high_precision': False}]


def main() -> int:
    run_nav_waypoints("BOX_528_1/move-pick2.py", WAYPOINTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
