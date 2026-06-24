#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility entry for the old demo offset script."""

from offset_move_common import run_offset


if __name__ == "__main__":
    run_offset(offset_l=(0, 0, -0.02), offset_r=(0, 0, -0.02))
