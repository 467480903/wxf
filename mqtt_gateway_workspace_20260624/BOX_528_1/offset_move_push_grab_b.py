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

from mqtt_common import run_ee_offsets


def main() -> int:
    # Mirrors /data/wxf/wxf/BOX_528_1/offset_move_push_grab_b.py:
    # left x = 0.085 + 0.04 - 0.015 = 0.110m
    # right x = 0.085 + 0.035 - 0.015 = 0.105m
    run_ee_offsets(
        "BOX_528_1/offset_move_push_grab_b.py",
        offset_l=(0.110, 0.0, 0.0),
        offset_r=(0.105, 0.0, 0.0),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
