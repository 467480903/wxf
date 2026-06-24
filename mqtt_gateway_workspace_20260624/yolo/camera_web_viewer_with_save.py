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

from mqtt_common import DEFAULT_HTTP_URL



def main() -> int:
    import argparse
    import json
    from urllib.request import urlopen
    parser = argparse.ArgumentParser(description="Gateway camera viewer shim for yolo/camera_web_viewer_with_save.py")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(f"Gateway UI: {DEFAULT_HTTP_URL}")
    print(f"Head RGB snapshot: {DEFAULT_HTTP_URL}/api/cameras/head_rgb/snapshot.jpg")
    print(f"Head depth snapshot: {DEFAULT_HTTP_URL}/api/cameras/head_depth/snapshot.jpg")
    if args.check:
        with urlopen(f"{DEFAULT_HTTP_URL}/api/cameras", timeout=5.0) as response:
            print(json.dumps(json.loads(response.read().decode("utf-8")), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
