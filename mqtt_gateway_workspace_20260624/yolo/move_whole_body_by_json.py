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

from mqtt_common import run_whole_body_json



def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Migrated whole-body JSON wrapper for yolo/move_whole_body_by_json.py")
    parser.add_argument("json_path", nargs="?", default="../positions/arm_default.json")
    parser.add_argument("--sync", action="store_true")
    args = parser.parse_args()
    run_whole_body_json(args.json_path, source_script="yolo/move_whole_body_by_json.py", sync_requested=args.sync)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
