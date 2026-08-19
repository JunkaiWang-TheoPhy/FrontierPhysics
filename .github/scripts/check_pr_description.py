#!/usr/bin/env python3
"""Check that a task PR's description follows the FrontierPhysics template.

A task PR is any PR that changes files under ``tasks/<task-id>/``. For those,
the PR body must keep every required section of
``.github/PULL_REQUEST_TEMPLATE.md`` — the shape of the reference submission
(PR #23) — including the form-formatted task information that mirrors the
task-contribution form. Non-task PRs are skipped.

Invoked by ``.github/workflows/pr-description.yml`` with the event payload and
the PR's changed-file list:

    python3 .github/scripts/check_pr_description.py \
        --event "$GITHUB_EVENT_PATH" \
        --changed-files changed_files.txt
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REQUIRED_TITLE_PREFIX = "[Task] "
REQUIRED_H2 = (
    "Motivation",
    "Task history",
    "Task",
    "Form-formatted task information for human reviewers",
    "Checklist",
    "Local test results",
    "Failure analysis",
    "Artifacts",
    "Credit",
)
REQUIRED_FORM_H3 = (
    "One-sentence description",
    "Public links",
    "Project dates",
    "Research goal at the start",
    "Deep-research prompt",
    "Rubric: papers to find",
    "Rubric: key references",
    "Rubric: key ideas",
    "Rubric: behaviors to avoid",
    "Implementation task description",
    "Workspace environment",
    "Software environment",
    "Verifier check-points",
    "Correct-answer workspace",
)
PLACEHOLDERS = ("your-task-id", "YYYY-MM-DD")
UNCHECKED_EXPLANATION = "Deliberately unchecked"

ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
UNCHECKED_BOX = re.compile(r"^[ \t]*[-*][ \t]+\[ \]", re.MULTILINE)
CHECKED_BOX = re.compile(r"^[ \t]*[-*][ \t]+\[[xX]\]", re.MULTILINE)
TABLE_SEPARATOR = re.compile(r"^\|[\s\-:|]+\|?\s*$")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def is_task_pr(changed_files: list[str]) -> bool:
    """A task PR changes at least one file inside a task directory."""
    return any(re.match(r"tasks/[^/]+/", path) for path in changed_files)


def _sections(body: str, level: str) -> dict[str, str]:
    """Map heading text to the content that follows it, for one heading level."""
    pattern = re.compile(rf"^{level} +(.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(body))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[match.group(1)] = body[start:end]
    return sections


def _has_table_data_row(section: str) -> bool:
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or TABLE_SEPARATOR.match(stripped):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if any(re.search(r"[0-9]", cell) for cell in cells):
            return True
    return False


def check(title: str, body: str) -> list[str]:
    """Return every problem with a task PR's title and description."""
    problems: list[str] = []

    if not title.strip().startswith(REQUIRED_TITLE_PREFIX):
        problems.append(f'title must start with "{REQUIRED_TITLE_PREFIX.strip()} " for task PRs; got {title.strip()!r}')

    body = HTML_COMMENT.sub("", body.replace("\r\n", "\n"))
    if not body.strip():
        problems.append("description is empty; fill in the task PR template")
        return problems

    h2 = _sections(body, "##")
    for heading in REQUIRED_H2:
        if heading not in h2:
            problems.append(f'missing required section "## {heading}"')

    h3 = _sections(body, "###")
    for heading in REQUIRED_FORM_H3:
        if heading not in h3:
            problems.append(f'missing required form subsection "### {heading}"')

    for placeholder in PLACEHOLDERS:
        if placeholder in body:
            problems.append(f"template placeholder {placeholder!r} was not replaced")

    history = h2.get("Task history", "")
    if history and len(ISO_DATE.findall(history)) < 2:
        problems.append("Task history must state the project start and end date (YYYY-MM-DD)")

    checklist = h2.get("Checklist", "")
    if checklist:
        if not CHECKED_BOX.search(checklist):
            problems.append("Checklist has no checked boxes")
        if UNCHECKED_BOX.search(checklist) and UNCHECKED_EXPLANATION not in body:
            problems.append(
                f'Checklist has unchecked boxes without a "{UNCHECKED_EXPLANATION}" explanation; check every box or explain the exception'
            )

    results = h2.get("Local test results", "")
    if results and not _has_table_data_row(results):
        problems.append("Local test results table has no data rows; report the runs you completed")

    credit = h2.get("Credit", "")
    if credit:
        author_row = re.search(r"^\|\s*Author\s*\|(?P<value>.*)$", credit, re.MULTILINE)
        if not author_row or not re.search(r"\w", author_row.group("value").replace("|", "")):
            problems.append("Credit table must name the task author")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True, help="path to the GitHub event payload JSON")
    parser.add_argument("--changed-files", required=True, help="path to a newline-separated changed-file list")
    args = parser.parse_args()

    event = json.loads(Path(args.event).read_text(encoding="utf-8"))
    pull_request = event.get("pull_request") or {}
    title = pull_request.get("title") or ""
    body = pull_request.get("body") or ""

    changed_files = [line.strip() for line in Path(args.changed_files).read_text(encoding="utf-8").splitlines() if line.strip()]

    if not is_task_pr(changed_files):
        print("OK: not a task PR (no files under tasks/<task-id>/); description check skipped")
        return 0

    problems = check(title, body)
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}")
        print(f"\nThe task PR description must follow .github/PULL_REQUEST_TEMPLATE.md ({len(problems)} problem(s) above).")
        return 1

    print("OK: task PR description follows the template")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
