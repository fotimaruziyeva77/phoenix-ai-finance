#!/usr/bin/env python3
"""Fail unless the interpreter is Python 3.12.x (project runtime standard).

Used in CI after ``actions/setup-python`` and can be run locally:
``python scripts/check_python_version.py``
"""
from __future__ import annotations

import sys

EXPECTED_MAJOR = 3
EXPECTED_MINOR = 12


def main() -> int:
    got = sys.version_info[:2]
    want = (EXPECTED_MAJOR, EXPECTED_MINOR)
    if got != want:
        print(
            f"BotForge AI requires Python {EXPECTED_MAJOR}.{EXPECTED_MINOR}.x "
            f"(Dockerfile + CI). This interpreter is {sys.version.split()[0]} "
            f"({got[0]}.{got[1]}).",
            file=sys.stderr,
        )
        print(
            "Use pyenv/asdf with `.python-version`, or `docker compose` for the backend.",
            file=sys.stderr,
        )
        return 1
    print(f"Python runtime OK: {sys.version.split()[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
