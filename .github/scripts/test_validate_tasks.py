#!/usr/bin/env python3
"""Behavioral tests for task layout and weighted-rubric validation."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_tasks as vt


def _write_task(root: Path, rubric: object | None) -> Path:
    task = root / "demo-task"
    for directory in (task / "environment", task / "oracle", task / "verifier"):
        directory.mkdir(parents=True, exist_ok=True)
    (task / "task.md").write_text("---\nname: demo-task\n---\n\nDo the research.\n", encoding="utf-8")
    (task / "environment" / "Dockerfile").write_text("FROM python:3.12\n", encoding="utf-8")
    (task / "oracle" / "solve.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (task / "verifier" / "test.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    if rubric is not None:
        (task / "verifier" / "rubric.json").write_text(json.dumps(rubric), encoding="utf-8")
    return task


def _criterion(**overrides: object) -> dict[str, object]:
    criterion: dict[str, object] = {
        "name": "scientific_quality",
        "blocker": 0,
        "weight": 5,
        "description": "Evidence: paper.pdf.",
        "guidance": "Evaluate the scientific result.",
    }
    criterion.update(overrides)
    return criterion


class TaskValidatorTests(unittest.TestCase):
    def check_rubric(self, rubric: object | None) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            task = _write_task(Path(tmp), rubric)
            return vt.problems_for_task(task)

    def assertProblem(self, problems: list[str], needle: str) -> None:
        self.assertTrue(any(needle in problem for problem in problems), f"{needle!r} not found in {problems!r}")

    def test_weighted_rubric_passes(self) -> None:
        self.assertEqual(self.check_rubric({"criteria": [_criterion()]}), [])

    def test_legacy_rubric_is_rejected(self) -> None:
        criterion = _criterion()
        del criterion["blocker"]
        del criterion["weight"]
        problems = self.check_rubric({"criteria": [criterion]})
        self.assertProblem(problems, "must contain exactly")

    def test_extra_rubric_field_is_rejected(self) -> None:
        problems = self.check_rubric({"criteria": [_criterion(score=2)]})
        self.assertProblem(problems, "extra ['score']")

    def test_blocker_must_be_zero_or_one(self) -> None:
        for blocker in (True, 2, "1"):
            with self.subTest(blocker=blocker):
                problems = self.check_rubric({"criteria": [_criterion(blocker=blocker)]})
                self.assertProblem(problems, "integer 0 or 1")

    def test_rubric_is_required(self) -> None:
        self.assertProblem(self.check_rubric(None), "missing verifier/rubric.json")


if __name__ == "__main__":
    unittest.main()
