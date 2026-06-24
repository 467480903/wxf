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
    run_arm_named_pose("Robot/move_arm_joint_box_grab.py", pose='move_arm_joint_box_grab', joint_positions=[0.866, -1.597, -1.142, -0.699, 1.206, 0.497, -0.735, -0.693, -1.643, 0.896, -0.429, -1.12, 0.157, 0.658])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
