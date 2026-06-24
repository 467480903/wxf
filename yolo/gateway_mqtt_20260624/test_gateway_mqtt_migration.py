#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static checks for the migrated yolo gateway scripts."""

from __future__ import annotations

import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FORBIDDEN = (
    "agibot" + "_gdk",
    "gdk" + "_init",
    "gdk" + "_release",
)


def main() -> int:
    failures: list[str] = []
    for path in sorted(ROOT.glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in FORBIDDEN:
            if token in text:
                failures.append(f"{path.name}: contains forbidden token {token!r}")
        py_compile.compile(str(path), doraise=True)
    if failures:
        for failure in failures:
            print(failure)
        return 1
    print("OK: top-level migrated python files compile and do not contain direct SDK init/release tokens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
