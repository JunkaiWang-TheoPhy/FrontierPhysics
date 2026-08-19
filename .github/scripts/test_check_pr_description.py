#!/usr/bin/env python3
"""Behavioral tests for the task PR description checker.

Run with the stdlib test runner (no third-party deps, matching the checker):

    python3 .github/scripts/test_check_pr_description.py

Each case builds a PR body from the checker's own required-section lists, so
the fixture cannot drift from the template contract.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_pr_description as cpd

TITLE = "[Task] Add demo-task task"


def _valid_sections() -> dict[str, str]:
    form = "\n".join(f"### {heading}\n\nFilled in for the demo task.\n" for heading in cpd.REQUIRED_FORM_H3)
    return {
        "Motivation": "Derived from my own trapped-ion experiment.",
        "Task history": (
            "| Report | Minimum | Value |\n"
            "|---|---|---|\n"
            "| Project time scale — start and end date | 2 weeks | 2023-07-24 → 2024-03-11 |\n"
            "| Actual working hours spent exploring the task | 40 hours | 100 hours |\n"
        ),
        "Task": "| Field | Value |\n|---|---|\n| Task ID | `demo-task` |\n",
        "Form-formatted task information for human reviewers": form,
        "Checklist": "- [x] `task.md` prompt body is concise, human-authored and outcome-focused\n",
        "Local test results": (
            "| Agent | Model | Reasoning | No skill (primary) | With skills (optional) | Time |\n"
            "|---|---|---|---:|---:|---:|\n"
            "| codex-acp | gpt | high | 0/2 | 2/2 | 30m |\n"
        ),
        "Failure analysis": "The no-skill run approximated the field solve.",
        "Artifacts": "Oracle output and verifier logs attached.",
        "Credit": "| Role | GitHub handle(s) |\n|---|---|\n| Author | @demo-author |\n",
    }


def _body(sections: dict[str, str]) -> str:
    return "\n".join(f"## {heading}\n\n{content}\n" for heading, content in sections.items())


class CheckTaskPrDescription(unittest.TestCase):
    def assertProblem(self, problems: list[str], needle: str) -> None:
        self.assertTrue(any(needle in problem for problem in problems), f"{needle!r} not found in {problems!r}")

    def assertNoProblem(self, problems: list[str], needle: str) -> None:
        self.assertFalse(any(needle in problem for problem in problems), f"unexpected {needle!r} in {problems!r}")

    def test_valid_body_passes(self) -> None:
        self.assertEqual(cpd.check(TITLE, _body(_valid_sections())), [])

    def test_title_must_carry_task_prefix(self) -> None:
        self.assertProblem(cpd.check("Add demo-task task", _body(_valid_sections())), "title must start")

    def test_empty_body_is_a_single_error(self) -> None:
        self.assertEqual(len(cpd.check(TITLE, "")), 1)
        self.assertProblem(cpd.check(TITLE, ""), "description is empty")

    def test_missing_required_section(self) -> None:
        sections = _valid_sections()
        del sections["Credit"]
        self.assertProblem(cpd.check(TITLE, _body(sections)), '"## Credit"')

    def test_missing_form_subsection(self) -> None:
        sections = _valid_sections()
        sections["Form-formatted task information for human reviewers"] = sections[
            "Form-formatted task information for human reviewers"
        ].replace("### Deep-research prompt", "### Renamed")
        self.assertProblem(cpd.check(TITLE, _body(sections)), '"### Deep-research prompt"')

    def test_task_history_requires_both_dates(self) -> None:
        sections = _valid_sections()
        sections["Task history"] = "| Project time scale | 2 weeks | soon |\n"
        self.assertProblem(cpd.check(TITLE, _body(sections)), "start and end date")

    def test_leftover_placeholder_fails(self) -> None:
        sections = _valid_sections()
        sections["Task"] = sections["Task"].replace("`demo-task`", "`your-task-id`")
        self.assertProblem(cpd.check(TITLE, _body(sections)), "'your-task-id'")

    def test_unchecked_box_needs_explanation(self) -> None:
        sections = _valid_sections()
        sections["Checklist"] += "- [ ] Dockerfile does not bake skills into the agent image\n"
        problems = cpd.check(TITLE, _body(sections))
        self.assertProblem(problems, "unchecked boxes")

        sections["Checklist"] += "\nDeliberately unchecked. The image ships no skills at all.\n"
        self.assertNoProblem(cpd.check(TITLE, _body(sections)), "unchecked boxes")

    def test_explanation_inside_html_comment_does_not_count(self) -> None:
        sections = _valid_sections()
        sections["Checklist"] += "- [ ] Oracle reaches reward `1.0`\n<!-- Deliberately unchecked -->\n"
        self.assertProblem(cpd.check(TITLE, _body(sections)), "unchecked boxes")

    def test_results_table_needs_a_data_row(self) -> None:
        sections = _valid_sections()
        sections["Local test results"] = (
            "| Agent | Model | Reasoning | No skill (primary) | With skills (optional) | Time |\n"
            "|---|---|---|---:|---:|---:|\n"
            "| | | | | | |\n"
        )
        self.assertProblem(cpd.check(TITLE, _body(sections)), "no data rows")

    def test_credit_must_name_the_author(self) -> None:
        sections = _valid_sections()
        sections["Credit"] = "| Role | GitHub handle(s) |\n|---|---|\n| Author | |\n"
        self.assertProblem(cpd.check(TITLE, _body(sections)), "name the task author")

    def test_is_task_pr(self) -> None:
        self.assertTrue(cpd.is_task_pr(["tasks/demo-task/task.md"]))
        self.assertTrue(cpd.is_task_pr(["README.md", "tasks/demo-task/verifier/test.sh"]))
        self.assertFalse(cpd.is_task_pr(["README.md", "website/src/App.tsx"]))
        self.assertFalse(cpd.is_task_pr(["tasks/.gitkeep"]))
        self.assertFalse(cpd.is_task_pr([]))


if __name__ == "__main__":
    unittest.main()
