#!/usr/bin/env python3
"""Tests for PR data-tree symlink containment."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_pr_data_tree as validator


class TreeContainmentTests(unittest.TestCase):
    def test_path_containment_helper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pr-head"
            self.assertTrue(validator._is_within(root, root))
            self.assertTrue(validator._is_within(root / "nested" / "file", root))
            self.assertFalse(validator._is_within(root.parent / "sibling", root))

    def test_regular_tree_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pr-head"
            (root / "tasks" / "demo").mkdir(parents=True)
            (root / "tasks" / "demo" / "task.md").write_text("prompt", encoding="utf-8")
            validator.validate_tree(root)

    def test_in_tree_symlink_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pr-head"
            target = root / ".agents" / "skills"
            link = root / ".claude" / "skills"
            target.mkdir(parents=True)
            link.parent.mkdir(parents=True)
            try:
                os.symlink(target, link, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlinks are unavailable: {exc}")
            validator.validate_tree(root)

    def test_out_of_tree_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "pr-head"
            root.mkdir()
            secret = base / "secret.env"
            secret.write_text("SECRET", encoding="utf-8")
            link = root / "task-link"
            try:
                os.symlink(secret, link)
            except OSError as exc:
                self.skipTest(f"symlinks are unavailable: {exc}")
            with self.assertRaisesRegex(validator.ContainmentError, "escapes"):
                validator.validate_tree(root)

    def test_dangling_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pr-head"
            root.mkdir()
            link = root / "missing-link"
            try:
                os.symlink(root / "missing", link)
            except OSError as exc:
                self.skipTest(f"symlinks are unavailable: {exc}")
            with self.assertRaisesRegex(validator.ContainmentError, "dangling"):
                validator.validate_tree(root)


if __name__ == "__main__":
    unittest.main()
