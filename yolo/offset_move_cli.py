#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
末端执行器偏移运动 CLI 版本
通过命令行参数指定左右臂的偏移量，复用 offset_move_common.run_offset。

坐标系：X+(向前)  Y+(向左)  Z+(向上)，单位为米

用法示例：
  # 左臂 Y-0.02，右臂 Y+0.02（向内）
  python offset_move_cli.py --lx 0 --ly -0.02 --lz 0 --rx 0 --ry 0.02 --rz 0

  # 左臂 Y+0.02，右臂 Y-0.02（向外）
  python offset_move_cli.py --ly 0.02 --ry -0.02

  # 仅左臂前推 0.05m
  python offset_move_cli.py --lx 0.05

  # 双手同时抬起 0.1m
  python offset_move_cli.py --lz 0.1 --rz 0.1

  # 不指定时默认全部为 0（即不动）
  python offset_move_cli.py
"""

import argparse
from offset_move_common import run_offset


def main():
    parser = argparse.ArgumentParser(
        description="末端执行器偏移运动（CLI）— 通过命令行参数指定左右臂偏移量",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # 左臂偏移参数（单位：米）
    parser.add_argument("--lx", type=float, default=0.0, help="左臂 X 偏移（向前为正），单位：米")
    parser.add_argument("--ly", type=float, default=0.0, help="左臂 Y 偏移（向左为正），单位：米")
    parser.add_argument("--lz", type=float, default=0.0, help="左臂 Z 偏移（向上为正），单位：米")

    # 右臂偏移参数（单位：米）
    parser.add_argument("--rx", type=float, default=0.0, help="右臂 X 偏移（向前为正），单位：米")
    parser.add_argument("--ry", type=float, default=0.0, help="右臂 Y 偏移（向左为正），单位：米")
    parser.add_argument("--rz", type=float, default=0.0, help="右臂 Z 偏移（向上为正），单位：米")

    args = parser.parse_args()

    offset_l = (args.lx, args.ly, args.lz)
    offset_r = (args.rx, args.ry, args.rz)

    print(f"左臂偏移 (X, Y, Z): {offset_l}")
    print(f"右臂偏移 (X, Y, Z): {offset_r}")

    run_offset(offset_l=offset_l, offset_r=offset_r)


if __name__ == "__main__":
    main()
