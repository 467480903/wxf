#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import time
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    _common = _parent / "mqtt_common"
    if _common.is_dir():
        sys.path.insert(0, str(_common))
        break

from mqtt_common import run_gripper



def main() -> int:
    source_script = "Robot/move_ee_pose_open_2.py"
    run_gripper('open', source_script=source_script, targets={'right': -0.785})
    time.sleep(0.02)
    run_gripper('open', source_script=source_script, targets={'left': -0.785})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
