#!/usr/bin/env python3
"""Reject PR-head symlinks that escape the untrusted data checkout."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


class ContainmentError(RuntimeError):
    """A safe validation failure for workflow logs."""


def _is_within(path: Path, root: Path) -> bool:
    """Return whether *path* is at or below *root* on Python 3.8+."""
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_tree(root: Path) -> None:
    """Require every symlink in *root* to resolve to an existing in-tree path."""
    if root.is_symlink():
        raise ContainmentError("PR data root must not be a symlink")
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise ContainmentError("PR data root is missing or unreadable") from exc
    if not resolved_root.is_dir():
        raise ContainmentError("PR data root is not a directory")

    pending = [resolved_root]
    while pending:
        directory = pending.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError as exc:
            raise ContainmentError("PR data tree contains an unreadable directory") from exc
        for entry in entries:
            path = Path(entry.path)
            if entry.is_symlink():
                try:
                    target = path.resolve(strict=True)
                except (OSError, RuntimeError) as exc:
                    raise ContainmentError(
                        f"PR data tree contains a dangling or cyclic symlink: {path.relative_to(resolved_root)}"
                    ) from exc
                if not _is_within(target, resolved_root):
                    raise ContainmentError(
                        f"PR data symlink escapes its checkout: {path.relative_to(resolved_root)}"
                    )
            elif entry.is_dir(follow_symlinks=False):
                pending.append(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        validate_tree(args.root)
    except ContainmentError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("PR data symlink containment: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
