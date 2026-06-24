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

from mqtt_common import run_waist_correction



def main() -> int:
    run_waist_correction("yolo/correct_waist.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
