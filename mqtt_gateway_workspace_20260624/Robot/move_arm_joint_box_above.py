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
    run_arm_named_pose("Robot/move_arm_joint_box_above.py", pose='move_arm_joint_box_above', joint_positions=[1.369, -1.651, -1.281, -1.796, 1.994, 0.316, -1.502, -1.344, -1.327, 1.348, -1.753, -1.358, 0.141, 1.082])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
