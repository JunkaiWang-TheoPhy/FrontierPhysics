#!/usr/bin/env python3
"""Gate task prose on GPTZero's document-level authorship probabilities.

This script is designed for the trusted side of the ``pull_request_target``
agent-review workflow.  The PR checkout is untrusted data: target files are
resolved beneath that checkout, symlinks are rejected, and only two bounded
prose documents per touched task are sent to GPTZero:

* the prompt body of ``task.md`` (YAML frontmatter removed), and
* the ``name``, ``description``, and ``guidance`` strings from ``rubric.json``.

The output deliberately excludes source text, sentence highlights, the raw API
response, and the API key.  Exit codes are stable for workflow orchestration:

* 0: every document passed;
* 1: at least one document failed the authorship threshold;
* 2: the check could not produce a trustworthy result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any

API_URL = "https://api.gptzero.me/v2/predict/text"
DEFAULT_THRESHOLD = 0.10
MAX_CHARACTERS = 50_000
MIN_CHARACTERS = 250
MAX_TASKS_PER_PR = 1
MAX_ATTEMPTS = 3
REQUEST_TIMEOUT_SECONDS = 60
PROBABILITY_TOLERANCE = Decimal("0.000001")
TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
RUBRIC_PROSE_FIELDS = ("name", "description", "guidance")


class CheckError(RuntimeError):
    """A sanitized error safe to write to logs and the review report."""


@dataclass(frozen=True)
class ScanTarget:
    task_id: str
    path: Path
    relative_path: str
    content_scope: str
    text: str
    source_sha256: str
    scanned_sha256: str


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def touched_task_ids(changed_files: Iterable[str]) -> list[str]:
    """Return validated task ids touched by a GitHub PR file list."""
    task_ids: set[str] = set()
    for raw_path in changed_files:
        # GitHub filenames are exact opaque strings. Never normalize leading or
        # trailing whitespace: doing so can turn a non-task path into a task
        # path and bind the review to unchanged content.
        path_text = raw_path
        if not path_text:
            continue
        if "\\" in path_text:
            raise CheckError("changed-file paths must use GitHub's forward-slash form")
        path = PurePosixPath(path_text)
        if path.is_absolute() or ".." in path.parts:
            raise CheckError("changed-file list contains an unsafe path")
        if len(path.parts) < 3 or path.parts[0] != "tasks":
            continue
        task_id = path.parts[1]
        if not TASK_ID.fullmatch(task_id):
            raise CheckError("changed-file list contains an invalid task id")
        task_ids.add(task_id)
    if not task_ids:
        raise CheckError("no task package was found in the changed-file list")
    if len(task_ids) > MAX_TASKS_PER_PR:
        raise CheckError(f"a single PR may scan at most {MAX_TASKS_PER_PR} task packages")
    return sorted(task_ids)


def load_changed_files_json(path: Path) -> list[str]:
    """Load a lossless GitHub filename array produced by trusted workflow code."""
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise CheckError("changed-file manifest is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise CheckError("changed-file manifest is not valid JSON") from exc
    if not isinstance(parsed, list) or not parsed:
        raise CheckError("changed-file manifest must be a non-empty JSON array")
    if any(not isinstance(item, str) or "\x00" in item or "\r" in item or "\n" in item for item in parsed):
        raise CheckError("changed-file manifest contains an invalid filename")
    return parsed


def _read_regular_utf8(path: Path, repo_root: Path) -> str:
    """Read a bounded regular UTF-8 file without following PR-controlled links."""
    root = repo_root.resolve(strict=True)
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise CheckError(f"review input escapes the PR checkout: {path.name}") from exc
    component = root
    for part in relative.parts:
        component /= part
        if component.is_symlink():
            raise CheckError(f"refusing symlinked review input: {path.name}")
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise CheckError(f"required review input is missing: {path.name}") from exc
    if not resolved.is_relative_to(root):
        raise CheckError(f"review input escapes the PR checkout: {path.name}")
    if not resolved.is_file():
        raise CheckError(f"required review input is not a regular file: {path.name}")
    if resolved.stat().st_size > MAX_CHARACTERS * 4:
        raise CheckError(f"review input is too large to scan safely: {path.name}")
    try:
        return resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise CheckError(f"review input is not valid UTF-8: {path.name}") from exc


def task_prompt_body(source: str) -> str:
    """Remove a leading YAML frontmatter block from a task Markdown file."""
    normalized = source.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.splitlines(keepends=True)
    if not lines or lines[0].rstrip() != "---":
        raise CheckError("task.md is missing its opening YAML frontmatter marker")
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip() in {"---", "..."}:
            body = "".join(lines[index + 1:]).strip()
            if not body:
                raise CheckError("task.md prompt body is empty")
            return body
    raise CheckError("task.md is missing its closing YAML frontmatter marker")


def rubric_prose(source: str) -> str:
    """Extract only the human-authored prose fields from rubric JSON."""
    try:
        parsed = json.loads(source)
    except json.JSONDecodeError as exc:
        raise CheckError("rubric.json is not valid JSON") from exc
    if not isinstance(parsed, Mapping) or not isinstance(parsed.get("criteria"), list):
        raise CheckError("rubric.json must contain a criteria list")

    blocks: list[str] = []
    for index, criterion in enumerate(parsed["criteria"]):
        if not isinstance(criterion, Mapping):
            raise CheckError(f"rubric criterion {index + 1} is not an object")
        values: list[str] = []
        for field in RUBRIC_PROSE_FIELDS:
            value = criterion.get(field)
            if not isinstance(value, str) or not value.strip():
                raise CheckError(f"rubric criterion {index + 1} has no non-empty {field}")
            values.append(value.strip())
        blocks.append("\n".join(values))
    if not blocks:
        raise CheckError("rubric.json has no criteria to scan")
    return "\n\n".join(blocks)


def _validate_scan_length(text: str, relative_path: str) -> None:
    characters = len(text)
    if characters < MIN_CHARACTERS:
        raise CheckError(f"{relative_path} has fewer than {MIN_CHARACTERS} scannable characters")
    if characters > MAX_CHARACTERS:
        raise CheckError(f"{relative_path} exceeds GPTZero's {MAX_CHARACTERS}-character scan limit")


def build_targets(repo_root: Path, task_ids: Iterable[str]) -> list[ScanTarget]:
    """Build the two safe, normalized scan inputs for every touched task."""
    root = repo_root.resolve(strict=True)
    targets: list[ScanTarget] = []
    for task_id in task_ids:
        task_dir = root / "tasks" / task_id
        if task_dir.is_symlink():
            raise CheckError(f"refusing symlinked task directory: {task_id}")
        task_md = task_dir / "task.md"
        rubric_json = task_dir / "verifier" / "rubric.json"

        task_source = _read_regular_utf8(task_md, root)
        task_text = task_prompt_body(task_source)
        task_relative = f"tasks/{task_id}/task.md"
        _validate_scan_length(task_text, task_relative)
        targets.append(
            ScanTarget(
                task_id=task_id,
                path=task_md,
                relative_path=task_relative,
                content_scope="prompt_body_without_yaml_frontmatter",
                text=task_text,
                source_sha256=_sha256(task_source),
                scanned_sha256=_sha256(task_text),
            )
        )

        rubric_source = _read_regular_utf8(rubric_json, root)
        rubric_text = rubric_prose(rubric_source)
        rubric_relative = f"tasks/{task_id}/verifier/rubric.json"
        _validate_scan_length(rubric_text, rubric_relative)
        targets.append(
            ScanTarget(
                task_id=task_id,
                path=rubric_json,
                relative_path=rubric_relative,
                content_scope="criterion_name_description_guidance",
                text=rubric_text,
                source_sha256=_sha256(rubric_source),
                scanned_sha256=_sha256(rubric_text),
            )
        )
    return targets


def _safe_probability(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CheckError(f"GPTZero response has a non-numeric {field} probability")
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise CheckError(f"GPTZero response has an out-of-range {field} probability")
    return number


def summarize_prediction(response: Mapping[str, Any], threshold: float) -> dict[str, Any]:
    """Validate and reduce a GPTZero response to score-only audit fields."""
    documents = response.get("documents")
    if not isinstance(documents, list) or len(documents) != 1 or not isinstance(documents[0], Mapping):
        raise CheckError("GPTZero response must contain exactly one document result")
    document = documents[0]
    probabilities = document.get("class_probabilities")
    if not isinstance(probabilities, Mapping):
        raise CheckError("GPTZero response is missing class_probabilities")

    human = _safe_probability(probabilities.get("human"), "human")
    ai = _safe_probability(probabilities.get("ai"), "ai")
    mixed = _safe_probability(probabilities.get("mixed"), "mixed")
    probability_sum = Decimal(str(human)) + Decimal(str(ai)) + Decimal(str(mixed))
    if abs(probability_sum - Decimal(1)) > PROBABILITY_TOLERANCE:
        raise CheckError("GPTZero class probabilities do not sum to one")

    predicted_class = document.get("predicted_class")
    classification = document.get("document_classification")
    confidence = document.get("confidence_category")
    if predicted_class not in {"human", "ai", "mixed"}:
        raise CheckError("GPTZero response has an unknown predicted_class")
    if classification not in {"HUMAN_ONLY", "AI_ONLY", "MIXED"}:
        raise CheckError("GPTZero response has an unknown document_classification")
    if confidence not in {"high", "medium", "low"}:
        raise CheckError("GPTZero response has an unknown confidence_category")

    # Decimal arithmetic preserves the strict boundary. Binary floats can make
    # 0.09 + 0.01 compare below 0.10 even though the decimal values are equal.
    authorship_risk_decimal = Decimal(str(ai)) + Decimal(str(mixed))
    authorship_risk = float(authorship_risk_decimal)
    passed = (
        authorship_risk_decimal < Decimal(str(threshold))
        and predicted_class == "human"
        and classification == "HUMAN_ONLY"
    )
    summary: dict[str, Any] = {
        "document_classification": classification,
        "predicted_class": predicted_class,
        "confidence_category": confidence,
        "human_probability": human,
        "ai_probability": ai,
        "mixed_probability": mixed,
        "authorship_risk": authorship_risk,
        "passed": passed,
    }
    for field in ("average_generated_prob", "completely_generated_prob"):
        if field in document:
            summary[field] = _safe_probability(document[field], field)
    for field in ("version", "neatVersion"):
        value = document.get(field, response.get(field))
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            summary[field] = str(value)[:100]
    return summary


class GPTZeroClient:
    """Small synchronous client with bounded retries and sanitized failures."""

    def __init__(
        self,
        api_key: str,
        *,
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key.strip():
            raise CheckError("GPTZERO_API_KEY is not configured")
        self._api_key = api_key
        self._opener = opener
        self._sleeper = sleeper

    def predict(self, document: str) -> Mapping[str, Any]:
        # Pin only the response schema. Omitting modelVersion keeps GPTZero's
        # current detector model while avoiding an unannounced schema rollout.
        payload = json.dumps(
            {"document": document, "apiVersion": "2023-12-11"},
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            API_URL,
            data=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "FrontierPhysics-agent-review/1.0",
                "x-api-key": self._api_key,
            },
            method="POST",
        )

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                with self._opener(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                    raw = response.read()
                parsed = json.loads(raw.decode("utf-8"))
                if not isinstance(parsed, Mapping):
                    raise CheckError("GPTZero returned a non-object JSON response")
                return parsed
            except urllib.error.HTTPError as exc:
                if exc.code == 429 or 500 <= exc.code <= 599:
                    if attempt < MAX_ATTEMPTS:
                        self._sleeper(float(2 ** (attempt - 1)))
                        continue
                    raise CheckError(f"GPTZero API remained unavailable after {MAX_ATTEMPTS} attempts (HTTP {exc.code})") from exc
                raise CheckError(f"GPTZero API rejected the request (HTTP {exc.code})") from exc
            except (TimeoutError, urllib.error.URLError) as exc:
                if attempt < MAX_ATTEMPTS:
                    self._sleeper(float(2 ** (attempt - 1)))
                    continue
                raise CheckError(f"GPTZero API did not respond after {MAX_ATTEMPTS} attempts") from exc
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise CheckError("GPTZero returned malformed JSON") from exc
        raise AssertionError("retry loop exhausted unexpectedly")


def run_check(
    repo_root: Path,
    changed_files: Iterable[str],
    client: GPTZeroClient,
    threshold: float = DEFAULT_THRESHOLD,
) -> tuple[dict[str, Any], int]:
    """Run all scans and return a sanitized report plus the stable exit code."""
    if not math.isfinite(threshold) or threshold <= 0.0 or threshold >= 1.0:
        raise CheckError("threshold must be between zero and one")

    task_ids = touched_task_ids(changed_files)
    targets = build_targets(repo_root, task_ids)
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for target in targets:
        try:
            prediction = summarize_prediction(client.predict(target.text), threshold)
        except CheckError as exc:
            errors.append({"path": target.relative_path, "message": str(exc)})
            break
        results.append(
            {
                "task_id": target.task_id,
                "path": target.relative_path,
                "content_scope": target.content_scope,
                "characters_scanned": len(target.text),
                "source_sha256": target.source_sha256,
                "scanned_sha256": target.scanned_sha256,
                **prediction,
            }
        )

    if any(not result["passed"] for result in results):
        # A later outage must not hide a detector failure already returned for
        # another document. Preserve any secondary error in the report.
        status = "fail"
        exit_code = 1
    elif errors:
        status = "error"
        exit_code = 2
    elif all(result["passed"] for result in results) and len(results) == len(targets):
        status = "pass"
        exit_code = 0
    else:
        status = "fail"
        exit_code = 1

    report: dict[str, Any] = {
        "schema_version": 1,
        "status": status,
        "threshold": threshold,
        "threshold_operator": "<",
        "score_definition": "class_probabilities.ai + class_probabilities.mixed",
        "score_interpretation": "document-level probability of AI-only or mixed authorship; not a percentage of AI-written words",
        "task_ids": task_ids,
        "results": results,
        "errors": errors,
    }
    return report, exit_code


def error_report(
    message: str,
    threshold: float,
    task_ids: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "error",
        "threshold": threshold,
        "threshold_operator": "<",
        "score_definition": "class_probabilities.ai + class_probabilities.mixed",
        "score_interpretation": "document-level probability of AI-only or mixed authorship; not a percentage of AI-written words",
        "task_ids": list(task_ids),
        "results": [],
        "errors": [{"path": "", "message": message}],
    }


def _write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _print_summary(report: Mapping[str, Any]) -> None:
    print(f"GPTZero AI-authorship check: {str(report['status']).upper()}")
    threshold = float(report["threshold"])
    for result in report.get("results", []):
        marker = "PASS" if result["passed"] else "FAIL"
        print(
            f"{marker}: {result['path']}: authorship risk "
            f"{float(result['authorship_risk']):.2%} (required < {threshold:.2%}); "
            f"classification {result['document_classification']}"
        )
    for error in report.get("errors", []):
        prefix = f"{error['path']}: " if error.get("path") else ""
        print(f"ERROR: {prefix}{error['message']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path, help="untrusted PR checkout root")
    parser.add_argument("--changed-files-json", required=True, type=Path, help="JSON array of PR filenames")
    parser.add_argument("--output", required=True, type=Path, help="sanitized JSON report path")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="strict AI-or-mixed probability threshold")
    args = parser.parse_args()

    task_ids: list[str] = []
    try:
        changed_files = load_changed_files_json(args.changed_files_json)
        task_ids = touched_task_ids(changed_files)
        client = GPTZeroClient(os.environ.get("GPTZERO_API_KEY", ""))
        report, exit_code = run_check(args.repo_root, changed_files, client, args.threshold)
    except (CheckError, OSError) as exc:
        report = error_report(str(exc), args.threshold, task_ids)
        exit_code = 2

    try:
        _write_report(args.output, report)
    except OSError as exc:
        print(f"ERROR: could not write sanitized GPTZero report: {exc}", file=sys.stderr)
        return 2
    _print_summary(report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
