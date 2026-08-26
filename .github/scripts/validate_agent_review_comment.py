#!/usr/bin/env python3
"""Validate an agent review before it crosses into a write-scoped job.

The review agent processes untrusted pull-request text, so its structured output
is untrusted too. This script accepts only the bounded comment grammar documented
in ``.github/agent-review/prompt.md``, binds detector claims to the hash-verified
GPTZero report, and emits a canonical comment plus machine-readable state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

MAX_COMMENT_BYTES = 16_384
MAX_COMMENT_WORDS = 500
MAX_AI_REPORT_BYTES = 128_000
HEADER = "## First-pass task review (automated)"
READY_HEADER = "## ✅ Ready for human review"
INCOMPLETE_HEADER = "## ⏳ Automated check incomplete"
HUMAN_HEADER = "### For the human reviewer (non-binding)"
LINT_HEADER = "### Lint notes (non-blocking)"
TRUSTED_AI_HEADER = "### GPTZero AI-authorship evidence (trusted)"
FOOTER = (
    "_Maintainers may override any finding here. Science acceptance is decided by "
    "human expert review._"
)
WRAPPED_FOOTER = (
    "_Maintainers may override any finding here. Science acceptance is decided by\n"
    "human expert review._"
)
READY_STATUS = (
    "**Blockers: 0** — all objective checks and the automated GPTZero "
    "authorship gate passed."
)
INCOMPLETE_STATUS = (
    "**Blockers: 0** — objective static review found no content blockers; "
    "the GPTZero check is unavailable, so readiness is withheld."
)
BLOCKED_STATUS = re.compile(
    r"^\*\*Blockers: ([1-9][0-9]*)\*\* — fix these and push; "
    r"this comment updates in place\.$"
)
STATUS_PREFIX = re.compile(r"^\*\*Blockers:")
TRACK_LINE = re.compile(
    r"^\*\*Track:\*\* (?P<tick>`?)"
    r"(experiment-track|theory-track|simulation-data-numerical-track|application-track)"
    r"(?P=tick)$"
)
TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
MENTION = re.compile(r"(?<![A-Za-z0-9_-])@[A-Za-z0-9][A-Za-z0-9-]*")
NUMBERED_BLOCKER = re.compile(r"^[1-9][0-9]*\. \*\*")
HTML_TAG = re.compile(r"<\s*/?\s*[A-Za-z][^>]*>", flags=re.DOTALL)
# Reject the beginning of a tag even when the closing ``>`` is absent.  In
# CommonMark, type-1 raw HTML blocks such as a bare ``<script`` line can extend
# through end-of-document and hide the trusted evidence appended below the
# agent-controlled prose.
HTML_TAG_PREFIX = re.compile(r"<\s*/?\s*[A-Za-z]")
HTML_ENTITY = re.compile(r"&(?:#[0-9]+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]+);")
# Deliberately conservative CommonMark subset: mask only a matched pair of
# single backticks with neither delimiter backslash-escaped. Ambiguous spans
# remain visible to the raw-HTML check and are rejected fail-closed.
INLINE_CODE = re.compile(r"(?<![\\`])`(?!`)[^`\n]*(?<!\\)`(?!`)")
MARKDOWN_INLINE_LINK = re.compile(r"!?\[[^\]]*\]\s*\([^)]*\)", flags=re.DOTALL)
MARKDOWN_REFERENCE_LINK = re.compile(r"!?\[[^\]]*\]\s*\[[^\]]*\]", flags=re.DOTALL)
MARKDOWN_REFERENCE_DEFINITION = re.compile(r"^\s{0,3}\[[^\]\n]+\]:", flags=re.MULTILINE)
CODE_FENCE = re.compile(r"^\s*(?:```|~~~)", flags=re.MULTILINE)
CREDENTIAL_PREFIX = re.compile(r"(?:sk-ant-|github_pat_|gh[opsu]_)", flags=re.IGNORECASE)


class ValidationError(RuntimeError):
    """A deterministic rejection reason safe to print in a workflow log."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_regular_bytes(path: Path, limit: int, label: str) -> bytes:
    if path.is_symlink():
        raise ValidationError(f"{label} must not be a symlink")
    try:
        if not path.is_file():
            raise ValidationError(f"{label} is missing or is not a regular file")
        size = path.stat().st_size
        if size == 0:
            raise ValidationError(f"{label} is empty")
        if size > limit:
            raise ValidationError(f"{label} exceeds the {limit}-byte limit")
        return path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"could not read {label}") from exc


def _load_ai_report(
    path: Path,
    expected_sha256: str,
    expected_status: str,
) -> Mapping[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValidationError("expected GPTZero report hash is invalid")
    raw = _read_regular_bytes(path, MAX_AI_REPORT_BYTES, "GPTZero report")
    if _sha256(raw) != expected_sha256:
        raise ValidationError("GPTZero report changed after the trusted scanner step")
    try:
        report = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("GPTZero report is not valid UTF-8 JSON") from exc
    if not isinstance(report, Mapping):
        raise ValidationError("GPTZero report must be a JSON object")
    if report.get("status") != expected_status:
        raise ValidationError("GPTZero report status does not match the immutable workflow status")
    if not isinstance(report.get("results"), list) or not isinstance(report.get("errors"), list):
        raise ValidationError("GPTZero report is missing results or errors")
    task_ids = report.get("task_ids")
    if (
        not isinstance(task_ids, list)
        or len(task_ids) != 1
        or not isinstance(task_ids[0], str)
        or TASK_ID.fullmatch(task_ids[0]) is None
    ):
        raise ValidationError("GPTZero report must identify exactly one valid task")
    threshold = report.get("threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValidationError("GPTZero report has an invalid threshold")
    return report


def _trusted_ai_summary(report: Mapping[str, Any]) -> str:
    """Render detector evidence from the hash-bound report, never agent prose."""
    status = report.get("status")
    task_id = str(report["task_ids"][0])
    threshold = float(report["threshold"])
    if status not in {"pass", "fail", "error"} or not math.isfinite(threshold):
        raise ValidationError("GPTZero report cannot be rendered safely")

    expected_paths = {
        f"tasks/{task_id}/task.md",
        f"tasks/{task_id}/verifier/rubric.json",
    }
    seen_paths: set[str] = set()
    result_lines: list[str] = []
    for result in report["results"]:
        if not isinstance(result, Mapping):
            raise ValidationError("GPTZero result has an invalid evidence schema")
        path = result.get("path")
        passed = result.get("passed")
        risk = result.get("authorship_risk")
        if (
            not isinstance(path, str)
            or path not in expected_paths
            or path in seen_paths
            or not isinstance(passed, bool)
            or isinstance(risk, bool)
            or not isinstance(risk, (int, float))
            or not math.isfinite(float(risk))
            or not 0.0 <= float(risk) <= 1.0
        ):
            raise ValidationError("GPTZero result has an invalid evidence schema")
        seen_paths.add(str(path))
        marker = "PASS" if passed else "FAIL"
        result_lines.append(
            f"- **{marker}** `{path}`: {float(risk):.2%} authorship risk "
            f"(required < {threshold:.2%})."
        )

    if status == "pass" and (seen_paths != expected_paths or report["errors"]):
        raise ValidationError("passing GPTZero report is incomplete")
    if status == "fail" and not any(
        isinstance(result, Mapping) and result.get("passed") is False
        for result in report["results"]
    ):
        raise ValidationError("failed GPTZero report has no failed result")

    lines = [
        TRUSTED_AI_HEADER,
        "",
        f"**Overall: {str(status).upper()}** — document-level AI-or-mixed "
        f"probability must be < {threshold:.2%}.",
    ]
    lines.extend(result_lines)
    if status == "error":
        lines.append("- **ERROR** No detector score was available; readiness is withheld.")
    elif report["errors"]:
        lines.append("- **ERROR** A later document scan was unavailable; the earlier failure still blocks readiness.")
    lines.extend(
        [
            "",
            "_These values are classification probabilities, not percentages of words written by AI._",
        ]
    )
    return "\n".join(lines)


def _normalize_comment(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("review comment is not valid UTF-8") from exc
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"
    # The historical prompt wrapped this fixed sentence for readability. Treat
    # that one exact presentation variant as the same trusted footer and emit
    # the canonical single-line form.
    if text.endswith(WRAPPED_FOOTER + "\n"):
        text = text.removesuffix(WRAPPED_FOOTER + "\n") + FOOTER + "\n"
    if any(ord(character) < 32 and character != "\n" for character in text):
        raise ValidationError("review comment contains a control character")
    if len(re.findall(r"\S+", text)) > MAX_COMMENT_WORDS:
        raise ValidationError(f"review comment exceeds the {MAX_COMMENT_WORDS}-word limit")
    if "<!--" in text or "-->" in text:
        raise ValidationError("review comment contains an HTML comment")
    # GitHub renders HTML-looking physics notation safely when the *entire*
    # construct is inside an inline-code span (for example, `<x^2>`). Check
    # original-source positions instead of deleting spans: a backtick that
    # starts inside an already-open HTML attribute must not hide that tag.
    inline_spans = [(match.start(), match.end()) for match in INLINE_CODE.finditer(text)]

    def inside_inline_code(start: int, end: int) -> bool:
        return any(span_start <= start and end <= span_end for span_start, span_end in inline_spans)

    if any(
        not inside_inline_code(match.start(), match.end())
        for match in HTML_TAG.finditer(text)
    ) or any(
        not inside_inline_code(match.start(), match.end())
        for match in HTML_TAG_PREFIX.finditer(text)
    ) or any(
        not inside_inline_code(match.start(), match.end())
        for match in re.finditer(r"<(?:\?|!)", text)
    ):
        raise ValidationError("review comment contains raw HTML")
    if HTML_ENTITY.search(text):
        raise ValidationError("review comment contains an HTML entity")
    if CODE_FENCE.search(text):
        raise ValidationError("review comment contains a fenced code block")
    if (
        MARKDOWN_INLINE_LINK.search(text)
        or MARKDOWN_REFERENCE_LINK.search(text)
        or MARKDOWN_REFERENCE_DEFINITION.search(text)
    ):
        raise ValidationError("review comment contains a Markdown link or image")
    if re.search(r"https?://", text, flags=re.IGNORECASE):
        raise ValidationError("review comment contains an external URL")
    if CREDENTIAL_PREFIX.search(text):
        raise ValidationError("review comment contains a credential-like token prefix")
    return text


def _section_blocker_count(lines: list[str]) -> int:
    headings = [index for index, line in enumerate(lines) if line == "### Blockers"]
    if len(headings) != 1:
        raise ValidationError("a blocked review must contain exactly one Blockers section")
    start = headings[0] + 1
    end = next(
        (index for index in range(start, len(lines)) if lines[index].startswith("### ")),
        len(lines),
    )
    return sum(bool(NUMBERED_BLOCKER.match(line)) for line in lines[start:end])


def _next_nonempty_index(lines: list[str], start: int) -> int | None:
    return next((index for index in range(start, len(lines)) if lines[index]), None)


def _require_detector_evidence(text: str, report: Mapping[str, Any]) -> None:
    failed_results = [
        result
        for result in report["results"]
        if isinstance(result, Mapping) and result.get("passed") is False
    ]
    if not failed_results:
        raise ValidationError("failed GPTZero status has no failed document result")
    if "GPTZero" not in text:
        raise ValidationError("failed review omits the GPTZero blocker")
    threshold = float(report["threshold"])
    for result in failed_results:
        path = result.get("path")
        risk = result.get("authorship_risk")
        classification = result.get("document_classification")
        confidence = result.get("confidence_category")
        if (
            not isinstance(path, str)
            or isinstance(risk, bool)
            or not isinstance(risk, (int, float))
            or not isinstance(classification, str)
            or not isinstance(confidence, str)
        ):
            raise ValidationError("failed GPTZero result has an invalid evidence schema")
        required_fragments = (path, classification, confidence)
        risk_fragments = {f"{float(risk):.{places}%}" for places in range(3)}
        threshold_fragments = {f"{threshold:.{places}%}" for places in range(3)}
        if (
            any(fragment not in text for fragment in required_fragments)
            or not any(fragment in text for fragment in risk_fragments)
            or not any(fragment in text for fragment in threshold_fragments)
        ):
            raise ValidationError(f"review omits trusted GPTZero evidence for {path}")


def _require_report_errors(text: str, report: Mapping[str, Any]) -> None:
    errors = report["errors"]
    if not errors:
        raise ValidationError("incomplete GPTZero status has no sanitized error")
    for error in errors:
        if not isinstance(error, Mapping) or not isinstance(error.get("message"), str):
            raise ValidationError("GPTZero error has an invalid schema")
        if error["message"] not in text:
            raise ValidationError("review omits the sanitized GPTZero error")


def validate_comment(
    comment_path: Path,
    ai_report_path: Path,
    *,
    expected_ai_report_sha256: str,
    expected_ai_status: str,
    head_sha: str,
    ready_mentions: str,
    forbidden_secret: str = "",
) -> tuple[str, dict[str, Any]]:
    """Return a canonical comment and immutable publisher metadata."""
    if expected_ai_status not in {"pass", "fail", "error"}:
        raise ValidationError("immutable GPTZero status is invalid")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", head_sha):
        raise ValidationError("expected pull-request head SHA is invalid")
    report = _load_ai_report(
        ai_report_path,
        expected_ai_report_sha256,
        expected_ai_status,
    )
    raw_comment = _read_regular_bytes(comment_path, MAX_COMMENT_BYTES, "review comment")
    text = _normalize_comment(raw_comment)
    if forbidden_secret and forbidden_secret in text:
        raise ValidationError("review comment contains a protected workflow credential")
    lines = text.splitlines()

    if not lines or lines[0] != HEADER or lines.count(HEADER) != 1:
        raise ValidationError("review comment must begin with exactly one automated-review header")
    short_head = head_sha[:7]
    task_id = str(report["task_ids"][0])
    expected_intro = f"_Static review of `{task_id}` at `{short_head}`."
    if len(lines) < 3 or lines[1] != "" or not lines[2].startswith(expected_intro):
        raise ValidationError("review comment is not bound to the expected task and head SHA")
    track_lines = [line for line in lines if line.startswith("**Track:**")]
    if len(track_lines) != 1 or TRACK_LINE.fullmatch(track_lines[0]) is None:
        raise ValidationError("review comment must contain exactly one allowed track")
    track_index = lines.index(track_lines[0])

    if lines.count(HUMAN_HEADER) != 1:
        raise ValidationError("review comment must contain exactly one human-review section")
    human_index = lines.index(HUMAN_HEADER)
    if lines.count(LINT_HEADER) > 1:
        raise ValidationError("review comment contains duplicate lint sections")
    lint_index = lines.index(LINT_HEADER) if LINT_HEADER in lines else None
    if lint_index is not None and lint_index <= human_index:
        raise ValidationError("lint section is out of order")
    if lines.count(FOOTER) != 1 or lines[-1] != FOOTER:
        raise ValidationError("review comment must end with the exact maintainer footer")
    human_end = lint_index if lint_index is not None else len(lines) - 1
    crux_lines = [line for line in lines[human_index + 1:human_end] if line.startswith("- **Crux**:")]
    if len(crux_lines) != 1:
        raise ValidationError("human-review section must contain exactly one Crux line")

    status_lines = [line for line in lines if STATUS_PREFIX.match(line)]
    if len(status_lines) != 1:
        raise ValidationError("review comment must contain exactly one blocker status line")
    status_line = status_lines[0]
    status_index = lines.index(status_line)
    if not (2 < track_index < status_index < human_index):
        raise ValidationError("track, status, and human-review sections are out of order")
    blocked_match = BLOCKED_STATUS.fullmatch(status_line)
    if status_line == READY_STATUS or status_line == INCOMPLETE_STATUS:
        blocker_count = 0
    elif blocked_match is not None:
        blocker_count = int(blocked_match.group(1))
        if blocker_count > 99:
            raise ValidationError("review comment reports an implausible blocker count")
    else:
        raise ValidationError("review comment has an unrecognized blocker status line")

    configured_mentions = MENTION.findall(ready_mentions)
    if " ".join(configured_mentions) != ready_mentions.strip():
        raise ValidationError("configured maintainer mentions are invalid")
    actual_mentions = MENTION.findall(text)
    if text.count("@") != len(actual_mentions):
        raise ValidationError("review comment contains an invalid mention token")

    ready_headings = lines.count(READY_HEADER)
    incomplete_headings = lines.count(INCOMPLETE_HEADER)
    blocker_headings = lines.count("### Blockers")
    cc_line = f"cc {ready_mentions.strip()} — this PR is ready for science review."

    if blocker_count > 0:
        if status_line != (
            f"**Blockers: {blocker_count}** — fix these and push; "
            "this comment updates in place."
        ):
            raise ValidationError("blocked review status is inconsistent")
        if (
            ready_headings
            or incomplete_headings
            or READY_STATUS in text
            or INCOMPLETE_STATUS in text
        ):
            raise ValidationError("blocked review contains a contradictory ready/incomplete heading")
        if actual_mentions:
            raise ValidationError("blocked review must not mention maintainers")
        expected_listed_blockers = min(blocker_count, 5)
        if _section_blocker_count(lines) != expected_listed_blockers:
            raise ValidationError("reported blocker count does not match the numbered blocker list")
        if not (status_index < lines.index("### Blockers") < human_index):
            raise ValidationError("Blockers section is out of order")
        review_state = "blocked"
    else:
        if blocker_headings:
            raise ValidationError("zero-blocker review must omit the Blockers section")
        if any(NUMBERED_BLOCKER.match(line) for line in lines):
            raise ValidationError("zero-blocker review contains a numbered blocker")
        if expected_ai_status == "pass":
            if (
                ready_headings != 1
                or incomplete_headings != 0
                or status_line != READY_STATUS
                or lines.count(cc_line) != 1
                or actual_mentions != configured_mentions
            ):
                raise ValidationError("ready review does not match the exact pass-state grammar")
            ready_index = lines.index(READY_HEADER)
            status_after_ready = _next_nonempty_index(lines, ready_index + 1)
            cc_after_status = (
                _next_nonempty_index(lines, status_after_ready + 1)
                if status_after_ready is not None
                else None
            )
            if (
                not (track_index < ready_index < human_index)
                or status_after_ready is None
                or lines[status_after_ready] != READY_STATUS
                or cc_after_status is None
                or lines[cc_after_status] != cc_line
                or not (cc_after_status < human_index)
            ):
                raise ValidationError("ready status must immediately follow the ready heading")
            review_state = "ready"
        elif expected_ai_status == "error":
            if (
                ready_headings != 0
                or incomplete_headings != 1
                or status_line != INCOMPLETE_STATUS
                or actual_mentions
            ):
                raise ValidationError("incomplete review does not match the exact error-state grammar")
            incomplete_index = lines.index(INCOMPLETE_HEADER)
            status_after_incomplete = _next_nonempty_index(lines, incomplete_index + 1)
            if (
                not (track_index < incomplete_index < human_index)
                or status_after_incomplete is None
                or lines[status_after_incomplete] != INCOMPLETE_STATUS
                or not (status_after_incomplete < human_index)
            ):
                raise ValidationError("incomplete status must immediately follow its heading")
            review_state = "incomplete"
        else:
            raise ValidationError("failed GPTZero gate cannot produce a zero-blocker review")

    if expected_ai_status == "fail":
        if blocker_count == 0:
            raise ValidationError("failed GPTZero gate must be represented by a blocker")
        _require_detector_evidence(text, report)
    if report["errors"]:
        _require_report_errors(text, report)

    trusted_ai_summary = _trusted_ai_summary(report)
    without_footer = text.removesuffix(FOOTER + "\n").rstrip()
    canonical = f"{without_footer}\n\n{trusted_ai_summary}\n\n{FOOTER}\n"
    canonical_bytes = canonical.encode("utf-8")
    metadata = {
        "schema_version": 1,
        "publishable": True,
        "review_state": review_state,
        "blocker_count": blocker_count,
        "comment_sha256": _sha256(canonical_bytes),
        "ai_report_sha256": expected_ai_report_sha256,
    }
    return canonical, metadata


def _write_new_regular(path: Path, content: str) -> None:
    if path.is_symlink():
        raise ValidationError(f"refusing symlinked output path: {path.name}")
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"could not write {path.name}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comment", required=True, type=Path)
    parser.add_argument("--ai-report", required=True, type=Path)
    parser.add_argument("--expected-ai-report-sha256", required=True)
    parser.add_argument("--expected-ai-status", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--ready-mentions", default="")
    parser.add_argument("--validated-comment", required=True, type=Path)
    parser.add_argument("--metadata-output", required=True, type=Path)
    args = parser.parse_args()

    try:
        comment, metadata = validate_comment(
            args.comment,
            args.ai_report,
            expected_ai_report_sha256=args.expected_ai_report_sha256,
            expected_ai_status=args.expected_ai_status,
            head_sha=args.head_sha,
            ready_mentions=args.ready_mentions,
            forbidden_secret=os.environ.get("FORBIDDEN_CLAUDE_TOKEN", ""),
        )
        _write_new_regular(args.validated_comment, comment)
        _write_new_regular(
            args.metadata_output,
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        )
    except ValidationError as exc:
        print(f"ERROR: agent review comment rejected: {exc}", file=sys.stderr)
        return 1
    print(
        "Agent review comment validated: "
        f"{metadata['review_state']} ({metadata['blocker_count']} blockers)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
