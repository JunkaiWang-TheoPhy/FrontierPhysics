#!/usr/bin/env python3
"""Behavioral tests for the trusted agent-review comment validator."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_ai_authorship as authorship
import validate_agent_review_comment as validator

HEAD_SHA = "abcdef1234567890abcdef1234567890abcdef12"
MENTIONS = "@maintainer-one @maintainer-two"


def _report(status: str, *, failed: bool = False, error: str | None = None) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    if status != "error" or failed:
        results.append(
            {
                "path": "tasks/demo-task/task.md",
                "passed": not failed,
                "authorship_risk": 0.42 if failed else 0.05,
                "document_classification": "AI_ONLY" if failed else "HUMAN_ONLY",
                "confidence_category": "high",
            }
        )
        results.append(
            {
                "path": "tasks/demo-task/verifier/rubric.json",
                "passed": True,
                "authorship_risk": 0.03,
                "document_classification": "HUMAN_ONLY",
                "confidence_category": "high",
            }
        )
    return {
        "schema_version": 1,
        "status": status,
        "threshold": 0.10,
        "task_ids": ["demo-task"],
        "results": results,
        "errors": [] if error is None else [{"path": "", "message": error}],
    }


def _prefix() -> str:
    return f"""{validator.HEADER}

_Static review of `demo-task` at `{HEAD_SHA[:7]}`. Blockers have objective criteria; everything else is non-binding guidance for the human reviewer._

**Track:** theory-track

"""


def _tail(note: str | None = None) -> str:
    lint = f"\n{validator.LINT_HEADER}\n- GPTZero: {note}\n" if note else ""
    return f"""
### For the human reviewer (non-binding)
- **Crux**: The task measures whether an agent can recover the physical result.
{lint}
{validator.FOOTER}
"""


def _ready_comment() -> str:
    return (
        _prefix()
        + f"""{validator.READY_HEADER}
{validator.READY_STATUS}
cc {MENTIONS} — this PR is ready for science review.
"""
        + _tail()
    )


def _blocked_comment(*, detector: bool = False, error: str | None = None) -> str:
    if detector:
        evidence = (
            "GPTZero authorship risk 42.00% (required < 10.00%); "
            "classification AI_ONLY; confidence high."
        )
        path = "tasks/demo-task/task.md"
    else:
        evidence = "The rubric omits a required scientific outcome."
        path = "tasks/demo-task/verifier/rubric.json"
    return (
        _prefix()
        + f"""**Blockers: 1** — fix these and push; this comment updates in place.

### Blockers
1. **Objective issue** (§22) — `{path}:1`
   Evidence: {evidence}
   Fix: Revise the human-authored text and push a new commit.
"""
        + _tail(error)
    )


def _incomplete_comment(message: str) -> str:
    return (
        _prefix()
        + f"""{validator.INCOMPLETE_HEADER}
{validator.INCOMPLETE_STATUS}
"""
        + _tail(message)
    )


class ValidatorTests(unittest.TestCase):
    def _validate(
        self,
        comment: str,
        report: dict[str, Any],
        *,
        expected_status: str | None = None,
        crlf: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            comment_path = root / "comment.md"
            report_path = root / "report.json"
            if crlf:
                comment = comment.replace("\n", "\r\n")
            comment_path.write_bytes(comment.encode("utf-8"))
            report_bytes = (json.dumps(report, sort_keys=True) + "\n").encode("utf-8")
            report_path.write_bytes(report_bytes)
            return validator.validate_comment(
                comment_path,
                report_path,
                expected_ai_report_sha256=hashlib.sha256(report_bytes).hexdigest(),
                expected_ai_status=expected_status or str(report["status"]),
                head_sha=HEAD_SHA,
                ready_mentions=MENTIONS,
            )

    def test_valid_ready_comment(self) -> None:
        canonical, metadata = self._validate(_ready_comment(), _report("pass"))
        self.assertEqual(metadata["review_state"], "ready")
        self.assertEqual(metadata["blocker_count"], 0)
        self.assertEqual(metadata["comment_sha256"], hashlib.sha256(canonical.encode()).hexdigest())
        self.assertIn(validator.TRUSTED_AI_HEADER, canonical)
        self.assertIn("**Overall: PASS**", canonical)
        self.assertIn("`tasks/demo-task/task.md`: 5.00% authorship risk", canonical)
        self.assertIn("`tasks/demo-task/verifier/rubric.json`: 3.00% authorship risk", canonical)
        self.assertTrue(canonical.rstrip().endswith(validator.FOOTER))

    def test_valid_content_blocker_with_passing_detector(self) -> None:
        _, metadata = self._validate(_blocked_comment(), _report("pass"))
        self.assertEqual(metadata["review_state"], "blocked")

    def test_valid_backtick_wrapped_track(self) -> None:
        comment = _blocked_comment().replace(
            "**Track:** theory-track", "**Track:** `theory-track`"
        )
        _, metadata = self._validate(comment, _report("pass"))
        self.assertEqual(metadata["review_state"], "blocked")

    def test_valid_historically_wrapped_footer_is_canonicalized(self) -> None:
        comment = _blocked_comment().replace(validator.FOOTER, validator.WRAPPED_FOOTER)
        canonical, metadata = self._validate(comment, _report("pass"))
        self.assertEqual(metadata["review_state"], "blocked")
        self.assertTrue(canonical.rstrip().endswith(validator.FOOTER))
        self.assertNotIn(validator.WRAPPED_FOOTER, canonical)

    def test_valid_inline_code_physics_notation_is_not_raw_html(self) -> None:
        comment = _blocked_comment().replace(
            validator.FOOTER,
            "- Worth checking the strict `<x^2>` ordering.\n\n" + validator.FOOTER,
        )
        _, metadata = self._validate(comment, _report("pass"))
        self.assertEqual(metadata["review_state"], "blocked")

    def test_rejects_html_between_escaped_backticks(self) -> None:
        comment = _blocked_comment().replace(
            validator.FOOTER,
            "- Unsafe escaped delimiters: \\`<details>\\`.\n\n" + validator.FOOTER,
        )
        with self.assertRaisesRegex(validator.ValidationError, "raw HTML"):
            self._validate(comment, _report("pass"))

    def test_rejects_html_between_mismatched_backtick_runs(self) -> None:
        comment = _blocked_comment().replace(
            validator.FOOTER,
            "- Unsafe mismatched delimiters: `<details>``.\n\n" + validator.FOOTER,
        )
        with self.assertRaisesRegex(validator.ValidationError, "raw HTML"):
            self._validate(comment, _report("pass"))

    def test_rejects_commonmark_special_html_openers(self) -> None:
        for opener in ("<![CDATA[", "<!DOCTYPE html>", "<?review instruction?>"):
            with self.subTest(opener=opener):
                comment = _blocked_comment().replace(
                    validator.FOOTER,
                    f"- Unsafe raw opener: {opener}\n\n" + validator.FOOTER,
                )
                with self.assertRaisesRegex(validator.ValidationError, "raw HTML"):
                    self._validate(comment, _report("pass"))

    def test_rejects_code_delimiter_that_starts_inside_html_attribute(self) -> None:
        comment = _blocked_comment().replace(
            validator.FOOTER,
            '- Unsafe precedence: <details title="`x">`.\n\n' + validator.FOOTER,
        )
        with self.assertRaisesRegex(validator.ValidationError, "raw HTML"):
            self._validate(comment, _report("pass"))

    def test_rejects_unterminated_tag_like_openers(self) -> None:
        for opener in ("<script", "<pre", "<style", "<textarea", "<details"):
            with self.subTest(opener=opener):
                comment = _blocked_comment().replace(
                    validator.FOOTER,
                    f"- Unsafe unterminated opener: {opener}\n\n" + validator.FOOTER,
                )
                with self.assertRaisesRegex(validator.ValidationError, "raw HTML"):
                    self._validate(comment, _report("pass"))

    def test_valid_detector_blocker(self) -> None:
        canonical, metadata = self._validate(_blocked_comment(detector=True), _report("fail", failed=True))
        self.assertEqual(metadata["review_state"], "blocked")
        self.assertIn("**Overall: FAIL**", canonical)

    def test_valid_detector_evidence_with_equivalent_percentage_formatting(self) -> None:
        comment = _blocked_comment(detector=True).replace(
            "42.00% (required < 10.00%)",
            "42.0%; the authorship risk must remain strictly below 10%",
        )
        canonical, metadata = self._validate(comment, _report("fail", failed=True))
        self.assertEqual(metadata["review_state"], "blocked")
        self.assertIn("42.00% authorship risk", canonical)

    def test_valid_incomplete_comment(self) -> None:
        message = "GPTZero API did not respond after 3 attempts"
        canonical, metadata = self._validate(_incomplete_comment(message), _report("error", error=message))
        self.assertEqual(metadata["review_state"], "incomplete")
        self.assertIn("**Overall: ERROR**", canonical)
        self.assertIn("No detector score was available", canonical)

    def test_trusted_summary_rejects_incomplete_passing_report(self) -> None:
        report = _report("pass")
        report["results"].pop()
        with self.assertRaisesRegex(validator.ValidationError, "passing GPTZero report is incomplete"):
            self._validate(_ready_comment(), report)

    def test_trusted_summary_rejects_noncanonical_result_path(self) -> None:
        report = _report("pass")
        report["results"][0]["path"] = ["not", "a", "path"]
        with self.assertRaisesRegex(validator.ValidationError, "invalid evidence schema"):
            self._validate(_ready_comment(), report)

    def test_rejects_credential_like_output(self) -> None:
        comment = _ready_comment().replace(
            validator.FOOTER,
            "sk-ant-oat01-redacted-example\n\n" + validator.FOOTER,
        )
        with self.assertRaisesRegex(validator.ValidationError, "credential-like"):
            self._validate(comment, _report("pass"))

    def test_checker_error_report_is_publishable_as_incomplete(self) -> None:
        message = "GPTZERO_API_KEY is not configured"
        report = authorship.error_report(message, 0.10, ["demo-task"])
        _, metadata = self._validate(_incomplete_comment(message), report)
        self.assertEqual(metadata["review_state"], "incomplete")

    def test_valid_failure_plus_secondary_error(self) -> None:
        message = "GPTZero API did not respond after 3 attempts"
        _, metadata = self._validate(
            _blocked_comment(detector=True, error=message),
            _report("fail", failed=True, error=message),
        )
        self.assertEqual(metadata["review_state"], "blocked")

    def test_crlf_is_canonicalized(self) -> None:
        canonical, _ = self._validate(_ready_comment(), _report("pass"), crlf=True)
        self.assertNotIn("\r", canonical)
        self.assertTrue(canonical.endswith("\n"))

    def test_rejects_duplicate_or_contradictory_status(self) -> None:
        comment = _blocked_comment().replace(
            validator.FOOTER,
            validator.READY_STATUS + "\n\n" + validator.FOOTER,
        )
        with self.assertRaisesRegex(validator.ValidationError, "exactly one blocker status"):
            self._validate(comment, _report("pass"))

    def test_rejects_ready_sentence_buried_in_blocked_comment(self) -> None:
        comment = _blocked_comment().replace(
            "Evidence: The rubric",
            f"Evidence: {validator.READY_STATUS} The rubric",
        )
        with self.assertRaisesRegex(validator.ValidationError, "contradictory"):
            self._validate(comment, _report("pass"))

    def test_rejects_blocker_count_list_mismatch(self) -> None:
        comment = _blocked_comment().replace("**Blockers: 1**", "**Blockers: 2**")
        with self.assertRaisesRegex(validator.ValidationError, "does not match"):
            self._validate(comment, _report("pass"))

    def test_allows_total_above_five_with_five_listed(self) -> None:
        first = _blocked_comment().replace("**Blockers: 1**", "**Blockers: 8**")
        entries = ""
        for index in range(2, 6):
            entries += (
                f"{index}. **Objective issue {index}** (§10) — `tasks/demo-task/task.md:{index}`\n"
                "   Evidence: The submitted package contains an objective mismatch.\n"
                "   Fix: Correct the mismatch and push a new commit.\n"
            )
        comment = first.replace(_tail(), entries + _tail())
        _, metadata = self._validate(comment, _report("pass"))
        self.assertEqual(metadata["blocker_count"], 8)

    def test_rejects_extra_mention(self) -> None:
        comment = _ready_comment().replace(
            validator.FOOTER,
            "@outsider\n\n" + validator.FOOTER,
        )
        with self.assertRaisesRegex(validator.ValidationError, "pass-state grammar"):
            self._validate(comment, _report("pass"))

    def test_rejects_embedded_marker_html_image_and_url(self) -> None:
        additions = (
            "<!-- frontierphysics-agent-review -->",
            "<script>alert(1)</script>",
            '<img\nsrc="//evil.invalid/pixel">',
            "![pixel](asset.png)",
            "[click](javascript:alert(1))",
            "![pixel][ref]\n[ref]: //evil.invalid/pixel",
            "https://example.invalid",
            "&#64;outsider",
            "```markdown\n## ✅ Ready for human review\n```",
        )
        for addition in additions:
            with self.subTest(addition=addition):
                with self.assertRaises(validator.ValidationError):
                    self._validate(_ready_comment() + addition, _report("pass"))

    def test_rejects_ready_state_wrapped_in_code_fence(self) -> None:
        comment = _ready_comment().replace(
            validator.READY_HEADER,
            f"```markdown\n{validator.READY_HEADER}",
        ).replace(
            f"cc {MENTIONS} — this PR is ready for science review.",
            f"cc {MENTIONS} — this PR is ready for science review.\n```",
        )
        with self.assertRaisesRegex(validator.ValidationError, "fenced"):
            self._validate(comment, _report("pass"))

    def test_rejects_missing_human_review_section_or_footer(self) -> None:
        for comment in (
            _ready_comment().replace(validator.HUMAN_HEADER, "### Notes"),
            _ready_comment().replace(validator.FOOTER, "_Different footer._"),
        ):
            with self.subTest(comment=comment[-80:]):
                with self.assertRaises(validator.ValidationError):
                    self._validate(comment, _report("pass"))

    def test_rejects_control_character(self) -> None:
        with self.assertRaisesRegex(validator.ValidationError, "control"):
            self._validate(_ready_comment() + "\x00", _report("pass"))

    def test_rejects_missing_head_binding(self) -> None:
        with self.assertRaisesRegex(validator.ValidationError, "head SHA"):
            self._validate(_ready_comment().replace(HEAD_SHA[:7], "1234567"), _report("pass"))

    def test_rejects_wrong_task_binding(self) -> None:
        with self.assertRaisesRegex(validator.ValidationError, "task and head"):
            self._validate(_ready_comment().replace("demo-task", "other-task"), _report("pass"))

    def test_rejects_ai_status_mismatch(self) -> None:
        with self.assertRaisesRegex(validator.ValidationError, "status does not match"):
            self._validate(_ready_comment(), _report("pass"), expected_status="fail")

    def test_rejects_modified_ai_report_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            comment_path = root / "comment.md"
            report_path = root / "report.json"
            comment_path.write_text(_ready_comment(), encoding="utf-8")
            report_path.write_text(json.dumps(_report("pass")), encoding="utf-8")
            with self.assertRaisesRegex(validator.ValidationError, "changed"):
                validator.validate_comment(
                    comment_path,
                    report_path,
                    expected_ai_report_sha256="0" * 64,
                    expected_ai_status="pass",
                    head_sha=HEAD_SHA,
                    ready_mentions=MENTIONS,
                )

    def test_rejects_omitted_detector_evidence(self) -> None:
        with self.assertRaisesRegex(validator.ValidationError, "GPTZero blocker|evidence"):
            self._validate(_blocked_comment(), _report("fail", failed=True))

    def test_rejects_symlinked_comment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            actual = root / "actual.md"
            link = root / "comment.md"
            report_path = root / "report.json"
            actual.write_text(_ready_comment(), encoding="utf-8")
            report_bytes = (json.dumps(_report("pass")) + "\n").encode()
            report_path.write_bytes(report_bytes)
            try:
                os.symlink(actual, link)
            except OSError as exc:
                self.skipTest(f"symlinks are unavailable: {exc}")
            with self.assertRaisesRegex(validator.ValidationError, "symlink"):
                validator.validate_comment(
                    link,
                    report_path,
                    expected_ai_report_sha256=hashlib.sha256(report_bytes).hexdigest(),
                    expected_ai_status="pass",
                    head_sha=HEAD_SHA,
                    ready_mentions=MENTIONS,
                )


if __name__ == "__main__":
    unittest.main()
