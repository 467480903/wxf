#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Safe runner for migrated task sequence scripts.

Default behavior is plan-only. ``--execute`` can run local migrated scripts and
local file copies/moves, but commands pointing outside this directory are
blocked so a sequence cannot silently fall back to the old motion scripts.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def classify_command(task_entry: str) -> tuple[str, list[str], str]:
    parts = shlex.split(task_entry)
    if not parts:
        return "empty", parts, "empty task"
    executable = parts[0]
    if executable in {"cp", "mv"}:
        return "local_file_op", parts, "local file operation"
    if executable.endswith("python") or executable.endswith("python3") or executable in {"python", "python3"}:
        script = parts[1] if len(parts) > 1 else ""
        if script.startswith("../") or os.path.isabs(script):
            return "blocked_external", parts, "external script path blocked"
        return "local_python", parts, "local migrated python script"
    if executable.startswith("yolo-env/") and len(parts) > 1:
        return "vision_python", parts, "vision script using original yolo virtualenv"
    return "blocked_unknown", parts, "unknown command shape blocked"


def _safe_local_path(raw: str) -> Path:
    path = (SCRIPT_DIR / raw).resolve()
    if SCRIPT_DIR not in path.parents and path != SCRIPT_DIR:
        raise ValueError(f"path escapes migrated directory: {raw}")
    return path


def _execute_file_op(parts: list[str]) -> int:
    if len(parts) != 3:
        print(f"文件操作只支持两个参数: {' '.join(parts)}")
        return 1
    src = _safe_local_path(parts[1])
    dst = _safe_local_path(parts[2])
    if parts[0] == "cp":
        shutil.copy2(src, dst)
    else:
        shutil.move(src, dst)
    return 0


def _execute_python(parts: list[str]) -> int:
    script = _safe_local_path(parts[1])
    if not script.exists():
        print(f"找不到本地迁移脚本: {script}")
        return 1
    cmd = [sys.executable, str(script), *parts[2:]]
    return subprocess.run(cmd, cwd=SCRIPT_DIR).returncode


def _execute_vision(parts: list[str]) -> int:
    venv_python = (SCRIPT_DIR.parent / "yolo-env" / "bin" / "python").resolve()
    script = _safe_local_path(parts[1])
    if not venv_python.exists():
        print(f"找不到视觉虚拟环境解释器: {venv_python}")
        return 1
    if not script.exists():
        print(f"找不到视觉脚本: {script}")
        return 1
    cmd = [str(venv_python), str(script), *parts[2:]]
    return subprocess.run(cmd, cwd=SCRIPT_DIR).returncode


def run_sequence(name: str, sequence: list[str], execute: bool = False) -> int:
    print(f"# {name}")
    print(f"# steps={len(sequence)}, mode={'execute' if execute else 'dry-run plan'}")
    for index, task_entry in enumerate(sequence, start=1):
        kind, parts, reason = classify_command(task_entry)
        print(f"[{index:02d}/{len(sequence):02d}] {kind}: {task_entry} ({reason})")
        if not execute:
            continue
        if kind.startswith("blocked") or kind == "empty":
            print("已拦截：该命令没有在迁移目录内安全执行")
            return 1
        if kind == "local_file_op":
            rc = _execute_file_op(parts)
        elif kind == "local_python":
            rc = _execute_python(parts)
        elif kind == "vision_python":
            rc = _execute_vision(parts)
        else:
            rc = 1
        if rc != 0:
            print(f"步骤失败: {task_entry} rc={rc}")
            return rc
    return 0


def parse_sequence_args(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--execute", action="store_true", help="执行本目录内的迁移脚本；默认只打印计划")
    return parser.parse_args()
