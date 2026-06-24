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

from mqtt_common import run_arm_named_pose



def main() -> int:
    run_arm_named_pose("Robot/right_to_left.py", pose='right_to_left', joint_positions=[0.749, -1.578, -0.986, -0.582, 1.07, 0.253, -0.955, -0.749, -1.578, 0.986, -0.582, -1.07, 0.253, 0.955])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
