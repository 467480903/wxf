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

from mqtt_common import submit_task, require_done



def main() -> int:
    result = submit_task('gdk.read_power_state', {"source_script": "Robot/get_chest_power_state.py"}, mode="read_only", timeout_s=10.0)
    require_done(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
