#!/usr/bin/env python3
"""Behavioral tests for the trusted GPTZero AI-authorship checker."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_ai_authorship as caa


def _prediction(
    *,
    human: float = 0.95,
    ai: float = 0.04,
    mixed: float = 0.01,
    predicted_class: str = "human",
    classification: str = "HUMAN_ONLY",
) -> dict[str, Any]:
    return {
        "version": "test-version",
        "documents": [
            {
                "predicted_class": predicted_class,
                "document_classification": classification,
                "confidence_category": "high",
                "class_probabilities": {"human": human, "ai": ai, "mixed": mixed},
                "average_generated_prob": ai + mixed,
                "completely_generated_prob": ai,
            }
        ],
    }


def _task_source(marker: str = "PROMPT_SENTINEL") -> str:
    prompt = f"{marker} A scientist describes a real experimental workflow in their own voice. "
    return "---\nschema_version: '1.3'\nmetadata:\n  author_name: Demo\n---\n\n" + prompt * 6


def _rubric_source(marker: str = "RUBRIC_SENTINEL") -> str:
    criteria = []
    for index in range(3):
        criteria.append(
            {
                "name": f"criterion_{index}",
                "blocker": index == 0,
                "weight": index + 1,
                "description": f"{marker} Check whether the reported physical result {index} is supported by the evidence.",
                "guidance": "Inspect the scientific artifact, its uncertainty analysis, and the cited reference before assigning a score.",
            }
        )
    return json.dumps({"criteria": criteria})


def _make_repo(root: Path, task_ids: tuple[str, ...] = ("demo-task",)) -> None:
    for task_id in task_ids:
        task_dir = root / "tasks" / task_id
        (task_dir / "verifier").mkdir(parents=True)
        (task_dir / "task.md").write_text(_task_source(task_id), encoding="utf-8")
        (task_dir / "verifier" / "rubric.json").write_text(_rubric_source(task_id), encoding="utf-8")


class FakeClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.documents: list[str] = []

    def predict(self, document: str) -> dict[str, Any]:
        self.documents.append(document)
        return self.responses.pop(0)


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class InputExtractionTests(unittest.TestCase):
    def test_task_prompt_body_removes_frontmatter(self) -> None:
        body = caa.task_prompt_body(_task_source())
        self.assertIn("PROMPT_SENTINEL", body)
        self.assertNotIn("schema_version", body)
        self.assertNotIn("author_name", body)

    def test_task_prompt_body_requires_closed_frontmatter(self) -> None:
        with self.assertRaisesRegex(caa.CheckError, "closing YAML"):
            caa.task_prompt_body("---\nschema_version: 1\nNo closing marker")

    def test_task_prompt_body_ignores_indented_fence_in_yaml_scalar(self) -> None:
        source = (
            "---\nmetadata:\n  description: |\n    ---\n    HUMAN_METADATA\n"
            "  author_name: Demo\n---\nAI_PROMPT_BODY\n"
        )
        self.assertEqual(caa.task_prompt_body(source), "AI_PROMPT_BODY")

    def test_task_prompt_body_accepts_trailing_space_on_column_zero_fence(self) -> None:
        source = "---   \nschema_version: 1\n---   \nPROMPT_BODY\n"
        self.assertEqual(caa.task_prompt_body(source), "PROMPT_BODY")

    def test_rubric_prose_keeps_only_authored_fields(self) -> None:
        prose = caa.rubric_prose(_rubric_source())
        self.assertIn("RUBRIC_SENTINEL", prose)
        self.assertIn("criterion_0", prose)
        self.assertNotIn('"weight"', prose)
        self.assertNotIn('"blocker"', prose)

    def test_rubric_prose_rejects_missing_guidance(self) -> None:
        source = json.dumps(
            {
                "criteria": [
                    {
                        "name": "demo",
                        "blocker": 0,
                        "weight": 1,
                        "description": "description",
                    }
                ]
            }
        )
        with self.assertRaisesRegex(caa.CheckError, "guidance"):
            caa.rubric_prose(source)

    def test_touched_task_ids_deduplicates(self) -> None:
        self.assertEqual(
            caa.touched_task_ids(
                [
                    "README.md",
                    "tasks/demo-task/task.md",
                    "tasks/demo-task/verifier/rubric.json",
                    "tasks/demo-task/environment/Dockerfile",
                ]
            ),
            ["demo-task"],
        )

    def test_touched_task_ids_rejects_traversal(self) -> None:
        with self.assertRaisesRegex(caa.CheckError, "unsafe path"):
            caa.touched_task_ids(["tasks/../secret/task.md"])

    def test_leading_space_cannot_create_task_scope(self) -> None:
        with self.assertRaisesRegex(caa.CheckError, "no task package"):
            caa.touched_task_ids([" tasks/demo-task/probe.txt"])

    def test_changed_file_json_rejects_newline_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "files.json"
            manifest.write_text(json.dumps(["tasks/demo/task.md\ntasks/hidden/task.md"]), encoding="utf-8")
            with self.assertRaisesRegex(caa.CheckError, "invalid filename"):
                caa.load_changed_files_json(manifest)

    def test_touched_task_ids_caps_api_usage(self) -> None:
        changed = [f"tasks/task-{index}/task.md" for index in range(caa.MAX_TASKS_PER_PR + 1)]
        with self.assertRaisesRegex(caa.CheckError, "at most"):
            caa.touched_task_ids(changed)

    def test_build_targets_rejects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _make_repo(root)
            (root / "tasks" / "demo-task" / "task.md").unlink()
            with self.assertRaisesRegex(caa.CheckError, "missing"):
                caa.build_targets(root, ["demo-task"])

    def test_build_targets_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _make_repo(root)
            task_md = root / "tasks" / "demo-task" / "task.md"
            actual = root / "actual-task.md"
            actual.write_text(_task_source(), encoding="utf-8")
            task_md.unlink()
            try:
                os.symlink(actual, task_md)
            except OSError as exc:
                self.skipTest(f"symlinks are unavailable: {exc}")
            with self.assertRaisesRegex(caa.CheckError, "symlinked"):
                caa.build_targets(root, ["demo-task"])

    def test_build_targets_rejects_symlinked_intermediate_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _make_repo(root, ("demo-task", "other-task"))
            verifier = root / "tasks" / "demo-task" / "verifier"
            rubric = verifier / "rubric.json"
            rubric.unlink()
            verifier.rmdir()
            try:
                os.symlink(root / "tasks" / "other-task" / "verifier", verifier, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks are unavailable: {exc}")
            with self.assertRaisesRegex(caa.CheckError, "symlinked"):
                caa.build_targets(root, ["demo-task"])


class ProbabilityTests(unittest.TestCase):
    def test_human_only_below_threshold_passes(self) -> None:
        result = caa.summarize_prediction(_prediction(), 0.10)
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(result["authorship_risk"], 0.05)

    def test_exact_threshold_fails(self) -> None:
        result = caa.summarize_prediction(_prediction(human=0.90, ai=0.10, mixed=0.0), 0.10)
        self.assertFalse(result["passed"])

    def test_split_exact_threshold_fails(self) -> None:
        result = caa.summarize_prediction(_prediction(human=0.90, ai=0.09, mixed=0.01), 0.10)
        self.assertFalse(result["passed"])

    def test_mixed_probability_cannot_slip_past_low_ai_probability(self) -> None:
        result = caa.summarize_prediction(
            _prediction(
                human=0.79,
                ai=0.01,
                mixed=0.20,
                predicted_class="human",
                classification="HUMAN_ONLY",
            ),
            0.10,
        )
        self.assertFalse(result["passed"])
        self.assertAlmostEqual(result["authorship_risk"], 0.21)

    def test_non_human_classification_fails_even_with_inconsistent_low_risk(self) -> None:
        result = caa.summarize_prediction(
            _prediction(
                human=0.95,
                ai=0.04,
                mixed=0.01,
                predicted_class="mixed",
                classification="MIXED",
            ),
            0.10,
        )
        self.assertFalse(result["passed"])

    def test_malformed_probability_schema_is_an_error(self) -> None:
        with self.assertRaisesRegex(caa.CheckError, "sum to one"):
            caa.summarize_prediction(_prediction(human=0.80, ai=0.10, mixed=0.0), 0.10)


class AggregationTests(unittest.TestCase):
    def test_each_file_is_scanned_independently_and_all_must_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _make_repo(root)
            client = FakeClient(
                [
                    _prediction(),
                    _prediction(human=0.05, ai=0.90, mixed=0.05, predicted_class="ai", classification="AI_ONLY"),
                ]
            )
            report, exit_code = caa.run_check(root, ["tasks/demo-task/environment/Dockerfile"], client)

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(len(report["results"]), 2)
        self.assertTrue(report["results"][0]["passed"])
        self.assertFalse(report["results"][1]["passed"])
        self.assertEqual(len(client.documents), 2)
        self.assertNotIn("schema_version", client.documents[0])
        self.assertNotIn('"weight"', client.documents[1])

    def test_multiple_tasks_are_rejected_before_api_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _make_repo(root, ("a-task", "b-task"))
            client = FakeClient([_prediction() for _ in range(4)])
            with self.assertRaisesRegex(caa.CheckError, "at most 1"):
                caa.run_check(
                    root,
                    ["tasks/b-task/task.md", "tasks/a-task/verifier/rubric.json"],
                    client,
                )
        self.assertEqual(client.documents, [])

    def test_known_failure_takes_precedence_over_later_api_error(self) -> None:
        class FailThenErrorClient:
            calls = 0

            def predict(self, _document: str) -> dict[str, Any]:
                self.calls += 1
                if self.calls == 1:
                    return _prediction(
                        human=0.05,
                        ai=0.90,
                        mixed=0.05,
                        predicted_class="ai",
                        classification="AI_ONLY",
                    )
                raise caa.CheckError("temporary API outage")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _make_repo(root)
            report, exit_code = caa.run_check(
                root,
                ["tasks/demo-task/task.md"],
                FailThenErrorClient(),  # type: ignore[arg-type]
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["results"][0]["passed"])
        self.assertEqual(report["errors"][0]["message"], "temporary API outage")

    def test_api_error_after_pass_remains_indeterminate(self) -> None:
        class PassThenErrorClient:
            calls = 0

            def predict(self, _document: str) -> dict[str, Any]:
                self.calls += 1
                if self.calls == 1:
                    return _prediction()
                raise caa.CheckError("temporary API outage")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _make_repo(root)
            report, exit_code = caa.run_check(
                root,
                ["tasks/demo-task/task.md"],
                PassThenErrorClient(),  # type: ignore[arg-type]
            )

        self.assertEqual(exit_code, 2)
        self.assertEqual(report["status"], "error")

    def test_error_report_can_preserve_validated_task_binding(self) -> None:
        report = caa.error_report("credential unavailable", 0.10, ["demo-task"])
        self.assertEqual(report["status"], "error")
        self.assertEqual(report["task_ids"], ["demo-task"])

    def test_report_contains_hashes_but_not_submitted_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _make_repo(root)
            report, exit_code = caa.run_check(root, ["tasks/demo-task/task.md"], FakeClient([_prediction(), _prediction()]))

        serialized = json.dumps(report)
        self.assertEqual(exit_code, 0)
        self.assertIn("source_sha256", serialized)
        self.assertNotIn("PROMPT_SENTINEL", serialized)
        self.assertNotIn("RUBRIC_SENTINEL", serialized)


class ClientTests(unittest.TestCase):
    def test_request_pins_schema_but_not_detector_model(self) -> None:
        seen_payload: dict[str, Any] = {}

        def opener(request: urllib.request.Request, *, timeout: int) -> FakeResponse:
            self.assertEqual(timeout, caa.REQUEST_TIMEOUT_SECONDS)
            data = request.data
            self.assertIsInstance(data, bytes)
            seen_payload.update(json.loads(data.decode("utf-8")))
            return FakeResponse(_prediction())

        client = caa.GPTZeroClient("secret-value", opener=opener, sleeper=lambda _delay: None)
        client.predict("submitted prose")
        self.assertEqual(seen_payload["apiVersion"], "2023-12-11")
        self.assertEqual(seen_payload["document"], "submitted prose")
        self.assertNotIn("modelVersion", seen_payload)

    def test_retries_transient_http_status_then_succeeds(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def opener(_request: object, *, timeout: int) -> FakeResponse:
            nonlocal calls
            self.assertEqual(timeout, caa.REQUEST_TIMEOUT_SECONDS)
            calls += 1
            if calls == 1:
                raise urllib.error.HTTPError(caa.API_URL, 429, "rate limited", {}, None)
            return FakeResponse(_prediction())

        client = caa.GPTZeroClient("secret-value", opener=opener, sleeper=sleeps.append)
        self.assertEqual(client.predict("long enough document")["version"], "test-version")
        self.assertEqual(calls, 2)
        self.assertEqual(sleeps, [1.0])

    def test_http_error_does_not_leak_key_or_response_body(self) -> None:
        secret = "do-not-print-this-key"

        def opener(_request: object, *, timeout: int) -> FakeResponse:
            del timeout
            raise urllib.error.HTTPError(caa.API_URL, 401, f"rejected {secret}", {}, None)

        client = caa.GPTZeroClient(secret, opener=opener, sleeper=lambda _delay: None)
        with self.assertRaises(caa.CheckError) as context:
            client.predict("submitted text must not appear in the error")
        message = str(context.exception)
        self.assertNotIn(secret, message)
        self.assertNotIn("submitted text", message)
        self.assertIn("HTTP 401", message)


if __name__ == "__main__":
    unittest.main()
