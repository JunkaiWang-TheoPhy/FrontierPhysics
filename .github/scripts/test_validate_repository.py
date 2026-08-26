#!/usr/bin/env python3
"""Behavioral tests for repository-level BenchFlow metadata validation."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_repository as vr

DEFAULT_SPECIFIER = ">=0.7.5,<0.8"


def _write_fixture(
    root: Path,
    *,
    registry_specifier: str = DEFAULT_SPECIFIER,
    project_specifier: str = DEFAULT_SPECIFIER,
) -> None:
    registry = [
        {
            "name": "frontierphysics",
            "version": "0.1-dev",
            "bench_version": registry_specifier,
            "tasks": [],
        }
    ]
    (root / "registry.json").write_text(json.dumps(registry), encoding="utf-8")
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "frontierphysics"\ndependencies = ["benchflow[sandbox-daytona]{project_specifier}"]\n',
        encoding="utf-8",
    )


class BenchflowContractTests(unittest.TestCase):
    def assertProblem(self, problems: list[str], needle: str) -> None:
        self.assertTrue(any(needle in problem for problem in problems), f"{needle!r} not found in {problems!r}")

    def check_fixture(self, **overrides: str) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fixture(root, **overrides)
            return vr.benchflow_contract_problems(root)

    def test_aligned_metadata_passes(self) -> None:
        self.assertEqual(self.check_fixture(), [])

    def test_mismatched_registry_specifier_fails(self) -> None:
        problems = self.check_fixture(registry_specifier=">=0.6.7,<0.7")
        self.assertProblem(problems, "must match")

    def test_aligned_future_specifier_passes(self) -> None:
        specifier = ">=0.8,<0.9"
        self.assertEqual(
            self.check_fixture(
                registry_specifier=specifier,
                project_specifier=specifier,
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
