#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from task_all_place_a import TASK_SEQUENCE  # noqa: E402

for _parent in Path(__file__).resolve().parents:
    _common = _parent / "mqtt_common"
    if _common.is_dir():
        sys.path.insert(0, str(_common))
        break

from mqtt_common import run_sequence  # noqa: E402


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Alias for the A placement/pack demo sequence; original source currently exists as task_all_place_a.py"
    )
    parser.add_argument("--execute", action="store_true", help="execute the MQTT fast sequence; default prints plan")
    args = parser.parse_args()
    return run_sequence("yolo/task_all_pack_a.py -> task_all_place_a.py", TASK_SEQUENCE, SCRIPT_DIR, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
