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



def run_offset(offset_l=(0.0, 0.0, 0.0), offset_r=(0.0, 0.0, 0.0)):
    run_ee_offsets("yolo/offset_move_common.py", offset_l=offset_l, offset_r=offset_r)


if __name__ == "__main__":
    run_offset()
