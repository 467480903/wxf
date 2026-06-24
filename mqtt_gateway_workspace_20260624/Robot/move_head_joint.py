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

from mqtt_common import run_head_named



def main() -> int:
    run_head_named("Robot/move_head_joint.py", yaw_rad=0.05, pitch_rad=0.05, roll_rad=0.05)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
