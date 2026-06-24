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
    run_ee_offsets("Robot/offset_move.py", offset_l=(0.0, 0.0, -0.01), offset_r=(0.0, 0.0, -0.01))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
