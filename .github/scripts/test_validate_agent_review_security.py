#!/usr/bin/env python3
"""Regression tests for the credential-bearing agent-review boundary."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]


def _load_validator() -> ModuleType:
    path = SCRIPT_DIR / "validate_agent_review_security.py"
    spec = importlib.util.spec_from_file_location("validate_agent_review_security", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load agent-review security validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


class AgentReviewSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        for relative in (
            ".github/workflows/agent-review.yml",
            ".github/agent-review/managed-settings.json",
            ".github/scripts/run_claude_in_bwrap.sh",
            ".github/scripts/claude_egress_proxy.py",
        ):
            source = REPO_ROOT / relative
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _assert_rejected(self, mutation: Callable[[Path], None]) -> None:
        mutation(self.root)
        with self.assertRaises(validator.SecurityValidationError):
            validator.validate_repository(self.root)

    def test_current_repository_policy_passes(self) -> None:
        validator.validate_repository(REPO_ROOT)

    def test_tool_family_expansion_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/workflows/agent-review.yml"
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace('--tools "Read,Skill"', '--tools "Read,Skill,Bash"'), encoding="utf-8")

        self._assert_rejected(mutate)

    def test_duplicate_claude_args_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/workflows/agent-review.yml"
            text = path.read_text(encoding="utf-8")
            marker = '            --tools "Read,Skill"\n'
            path.write_text(
                text.replace(marker, marker + "          claude_args: >-\n            --tools Bash\n"),
                encoding="utf-8",
            )

        self._assert_rejected(mutate)

    def test_wrapper_action_input_removal_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/workflows/agent-review.yml"
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("          path_to_claude_code_executable:", "          ignored_executable:"), encoding="utf-8")

        self._assert_rejected(mutate)

    def test_action_pin_drift_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/workflows/agent-review.yml"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace("uses: anthropics/claude-code-action@16b3b310", "uses: anthropics/claude-code-action@deadbeef16b3b310"),
                encoding="utf-8",
            )

        self._assert_rejected(mutate)

    def test_disabled_review_step_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/workflows/agent-review.yml"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace(
                    "        if: steps.gate.outputs.ok == 'true'\n        uses: anthropics/claude-code-action",
                    "        if: ${{ false }}\n        uses: anthropics/claude-code-action",
                ),
                encoding="utf-8",
            )

        self._assert_rejected(mutate)

    def test_additional_credential_bearing_step_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/workflows/agent-review.yml"
            text = path.read_text(encoding="utf-8")
            marker = "      - name: Validate structured review output\n"
            unsafe_step = (
                "      - name: Unsafe extra token consumer\n"
                "        env:\n"
                "          CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}\n"
                "        run: true\n\n"
            )
            path.write_text(text.replace(marker, unsafe_step + marker), encoding="utf-8")

        self._assert_rejected(mutate)

    def test_structured_output_token_unset_removal_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/workflows/agent-review.yml"
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("          unset FORBIDDEN_CLAUDE_TOKEN\n", ""), encoding="utf-8")

        self._assert_rejected(mutate)

    def test_structured_output_local_token_check_removal_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/workflows/agent-review.yml"
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("             && comment_excludes_forbidden_token \\\n", ""), encoding="utf-8")

        self._assert_rejected(mutate)

    def test_review_runner_drift_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/workflows/agent-review.yml"
            text = path.read_text(encoding="utf-8")
            old = "    runs-on: ${{ vars.CI_MODE == 'github' && 'ubuntu-latest' || 'trusted' }}\n    timeout-minutes: 30"
            path.write_text(text.replace(old, "    runs-on: self-hosted\n    timeout-minutes: 30"), encoding="utf-8")

        self._assert_rejected(mutate)

    def test_mcp_strictness_removal_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/workflows/agent-review.yml"
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("            --strict-mcp-config\n", ""), encoding="utf-8")

        self._assert_rejected(mutate)

    def test_additional_cli_flag_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/workflows/agent-review.yml"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace(
                    "            --strict-mcp-config\n", "            --strict-mcp-config\n            --dangerously-skip-permissions\n"
                ),
                encoding="utf-8",
            )

        self._assert_rejected(mutate)

    def test_credential_during_install_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/workflows/agent-review.yml"
            text = path.read_text(encoding="utf-8")
            marker = "      - name: Prepare isolated Claude runtime\n"
            insertion = marker + "        env:\n          CLAUDE_CODE_OAUTH_TOKEN: unsafe\n"
            path.write_text(text.replace(marker, insertion), encoding="utf-8")

        self._assert_rejected(mutate)

    def test_managed_bash_allow_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/agent-review/managed-settings.json"
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            data["permissions"]["allow"].append("Bash")
            path.write_text(json.dumps(data), encoding="utf-8")

        self._assert_rejected(mutate)

    def test_managed_mcp_deny_removal_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/agent-review/managed-settings.json"
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            data["permissions"]["deny"].remove("mcp__*")
            path.write_text(json.dumps(data), encoding="utf-8")

        self._assert_rejected(mutate)

    def test_managed_bypass_enablement_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/agent-review/managed-settings.json"
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            data["permissions"]["disableBypassPermissionsMode"] = "allow"
            path.write_text(json.dumps(data), encoding="utf-8")

        self._assert_rejected(mutate)

    def test_unreviewed_managed_setting_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/agent-review/managed-settings.json"
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            data["enableAllProjectMcpServers"] = True
            path.write_text(json.dumps(data), encoding="utf-8")

        self._assert_rejected(mutate)

    def test_network_namespace_removal_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/scripts/run_claude_in_bwrap.sh"
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("  --unshare-net\n", ""), encoding="utf-8")

        self._assert_rejected(mutate)

    def test_proxy_removal_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/scripts/run_claude_in_bwrap.sh"
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("--setenv HTTPS_PROXY http://127.0.0.1:3128", ""), encoding="utf-8")

        self._assert_rejected(mutate)

    def test_egress_allowlist_expansion_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".github/scripts/claude_egress_proxy.py"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace(
                    '"platform.claude.com"}',
                    '"platform.claude.com", "example.com"}',
                ),
                encoding="utf-8",
            )

        self._assert_rejected(mutate)


if __name__ == "__main__":
    unittest.main()
