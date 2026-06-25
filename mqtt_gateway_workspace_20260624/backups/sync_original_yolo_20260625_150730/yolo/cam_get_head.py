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

from mqtt_common import fetch_gateway_snapshot



def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Fetch head snapshots through Gateway HTTP for yolo/cam_get_head.py")
    parser.add_argument("--timeout-s", type=float, default=5.0)
    args = parser.parse_args()
    fetch_gateway_snapshot("head_rgb", "head.jpg", timeout_s=args.timeout_s)
    try:
        fetch_gateway_snapshot("head_depth", "head_depth.jpg", timeout_s=args.timeout_s)
    except Exception as exc:
        print(f"depth snapshot skipped: {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
