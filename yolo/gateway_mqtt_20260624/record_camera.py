#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Record head RGB snapshots from the gateway HTTP interface."""

from __future__ import annotations

import argparse

from gateway_compat import record_gateway_snapshots


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval-s", type=float, default=0.5)
    parser.add_argument("--camera-id", default="head_rgb")
    parser.add_argument("--out-dir", default="images")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    record_gateway_snapshots(camera_id=args.camera_id, interval_s=args.interval_s, out_dir=args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
