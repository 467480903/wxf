#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility shim for the old camera web viewer."""

from __future__ import annotations

import argparse
import json
from urllib.request import urlopen

from gateway_compat import GATEWAY_HTTP_URL


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="检查网关 /api/cameras 配置")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(f"相机页面已迁移到网关 UI: {GATEWAY_HTTP_URL}")
    print(f"RGB 快照: {GATEWAY_HTTP_URL}/api/cameras/head_rgb/snapshot.jpg")
    print(f"深度快照: {GATEWAY_HTTP_URL}/api/cameras/head_depth/snapshot.jpg")
    if args.check:
        with urlopen(f"{GATEWAY_HTTP_URL}/api/cameras", timeout=5.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
