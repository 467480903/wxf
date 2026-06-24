#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch head camera snapshots from the gateway HTTP interface."""

from __future__ import annotations

import argparse

from gateway_compat import fetch_gateway_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-s", type=float, default=5.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fetch_gateway_snapshot("head_rgb", "head.jpg", timeout_s=args.timeout_s)
    try:
        fetch_gateway_snapshot("head_depth", "head_depth.jpg", timeout_s=args.timeout_s)
    except Exception as exc:  # noqa: BLE001 - depth can be disabled while RGB still works
        print(f"深度快照未保存: {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
