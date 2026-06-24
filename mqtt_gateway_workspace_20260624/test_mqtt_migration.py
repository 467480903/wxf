#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FORBIDDEN = ("agibot" + "_gdk", "gdk" + "_init", "gdk" + "_release")
PRUNE_DIRS = {"__pycache__", "yolo-env"}


def should_skip(path: Path) -> bool:
    return any(part in PRUNE_DIRS for part in path.relative_to(ROOT).parts)


def main() -> int:
    failures: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        if should_skip(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in FORBIDDEN:
            if token in text:
                failures.append(f"{path.relative_to(ROOT)} contains forbidden token {token!r}")
        py_compile.compile(str(path), doraise=True)
    if failures:
        for item in failures:
            print(item)
        return 1
    print("OK: migrated workspace python files compile and contain no direct SDK init/release tokens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
