#!/usr/bin/env python3
"""Fail when a hand-written Python source exceeds the maintainability limit."""

from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_ROOTS = ("src", "scripts", "services", "tests", "tools")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-lines", type=int, default=300)
    parser.add_argument("roots", nargs="*", default=DEFAULT_ROOTS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    violations = []
    for root_name in args.roots:
        root = Path(root_name)
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if any(part in {"__pycache__", ".venv", "build"} for part in path.parts):
                continue
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            if line_count > args.max_lines:
                violations.append((path, line_count))
    if violations:
        details = "\n".join(f"{path}: {lines}" for path, lines in violations)
        raise SystemExit(f"Python files exceed {args.max_lines} lines:\n{details}")


if __name__ == "__main__":
    main()
