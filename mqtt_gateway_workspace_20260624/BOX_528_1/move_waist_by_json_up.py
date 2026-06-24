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

from mqtt_common import run_waist_json


DEFAULT_JSON_PATH = '/data/wxf/wxf/positions/waist_position_to_up.json'


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Migrated waist JSON wrapper for BOX_528_1/move_waist_by_json_up.py")
    parser.add_argument("json_path", nargs="?", default=DEFAULT_JSON_PATH)
    args = parser.parse_args()
    run_waist_json(args.json_path, source_script="BOX_528_1/move_waist_by_json_up.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
