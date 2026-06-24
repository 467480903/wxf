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

from mqtt_common import record_gateway_snapshots



def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Record snapshots through Gateway HTTP for yolo/record_camera.py")
    parser.add_argument("--interval-s", type=float, default=0.5)
    parser.add_argument("--camera-id", default="head_rgb")
    parser.add_argument("--out-dir", default="images")
    args = parser.parse_args()
    record_gateway_snapshots(args.camera_id, interval_s=args.interval_s, out_dir=args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
