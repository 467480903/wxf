#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gateway-backed replacement for the original relative end-effector helper."""

from __future__ import annotations

import os
from typing import Iterable

from gateway_compat import require_done, safe_motion_mode, submit_task


def _as_offset(values: Iterable[float]) -> tuple[float, float, float]:
    item = tuple(float(v) for v in values)
    if len(item) != 3:
        raise ValueError("offset must contain exactly 3 numbers: dx, dy, dz")
    return item


def _submit_one(side: str, offset: tuple[float, float, float]) -> dict:
    dx, dy, dz = offset
    return submit_task(
        "ee.relative_offset",
        {
            "side": side,
            "dx_m": dx,
            "dy_m": dy,
            "dz_m": dz,
            "frame": "tool",
            "source_script": os.path.basename(__file__),
        },
        mode=safe_motion_mode(),
        timeout_s=10.0,
    )


def run_offset(offset_l=(0.0, 0.0, 0.0), offset_r=(0.0, 0.0, 0.0)):
    left = _as_offset(offset_l)
    right = _as_offset(offset_r)
    print(f"提交末端相对偏移到网关 dry-run: left={left}, right={right}")
    results = [_submit_one("left", left), _submit_one("right", right)]
    for result in results:
        require_done(result)
    return results
