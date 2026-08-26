#!/usr/bin/env python3
"""Fail closed when the credential-bearing agent-review boundary drifts."""

from __future__ import annotations

import argparse
import ast
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

EXPECTED_TOOLS = "Read,Skill"
EXPECTED_EGRESS_HOSTS = frozenset({"api.anthropic.com", "platform.claude.com"})
EXPECTED_EGRESS_PORT = 443
EXPECTED_ACTION = "anthropics/claude-code-action@16b3b310c3d7b5279df73130324d5205aeea8eac # v1.0.205"
EXPECTED_WRAPPER_INPUT = "${{ github.workspace }}/.github/scripts/run_claude_in_bwrap.sh"
EXPECTED_OAUTH_INPUT = "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}"
EXPECTED_OAUTH_LINES = (
    f"claude_code_oauth_token: {EXPECTED_OAUTH_INPUT}",
    f"FORBIDDEN_CLAUDE_TOKEN: {EXPECTED_OAUTH_INPUT}",
)
EXPECTED_FORBIDDEN_TOKEN_LINES = (
    f"FORBIDDEN_CLAUDE_TOKEN: {EXPECTED_OAUTH_INPUT}",
    "forbidden_claude_token=$FORBIDDEN_CLAUDE_TOKEN",
    "unset FORBIDDEN_CLAUDE_TOKEN",
)
EXPECTED_REVIEW_RUNNER = "${{ vars.CI_MODE == 'github' && 'ubuntu-latest' || 'trusted' }}"
EXPECTED_CLAUDE_FLAGS = (
    "--model",
    "--max-turns",
    "--permission-mode",
    "--setting-sources",
    "--strict-mcp-config",
    "--json-schema",
    "--tools",
    "--allowedTools",
    "--disallowedTools",
)
EXPECTED_ALLOW = (
    "Read(/pr-head/**)",
    "Read(/pr-head-scripts-as-submitted/**)",
    "Read(/.agents/skills/task-review/**)",
    "Read(/.github/agent-review/**)",
    "Read(/CONTRIBUTING.md)",
    "Read(/taxonomy.md)",
    "Read(/changed_files.json)",
    "Read(/review_files.json)",
    "Read(/pr_meta.json)",
    "Read(/advisory_checks.txt)",
    "Read(/ai_detection.json)",
    "Skill(task-review)",
)
EXPECTED_DENY = (
    "mcp__*",
    "Grep",
    "Glob",
    "Read(//proc/**)",
    "Read(//etc/**)",
    "Read(//**/.env)",
    "Read(//**/.env.*)",
    "Read(~/.ssh/**)",
    "Read(~/.aws/**)",
    "Read(~/.claude/**)",
    "Read(/.git/**)",
    "Read(/pr-head/.git/**)",
    "Agent",
    "AskUserQuestion",
    "Bash",
    "Edit",
    "Write",
    "NotebookEdit",
    "WebFetch",
    "WebSearch",
    "Task",
)


class SecurityValidationError(RuntimeError):
    """A deterministic, non-secret validation failure."""


def _read_regular_text(path: Path, label: str) -> str:
    if path.is_symlink() or not path.is_file():
        raise SecurityValidationError(f"{label} must be a regular non-symlink file")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SecurityValidationError(f"could not read {label}") from exc


def _extract_step(workflow: str, name: str) -> str:
    lines = workflow.splitlines()
    marker = f"- name: {name}"
    starts = [index for index, line in enumerate(lines) if line.strip() == marker]
    if len(starts) != 1:
        raise SecurityValidationError(f"workflow must contain exactly one {name!r} step")
    start = starts[0]
    indent = len(lines[start]) - len(lines[start].lstrip())
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].lstrip()
        current_indent = len(lines[index]) - len(stripped)
        if current_indent == indent and re.match(r"^-\s", stripped):
            end = index
            break
    return "\n".join(lines[start:end])


def _extract_mapping_block(document: str, key: str, indent: int, label: str) -> str:
    lines = document.splitlines()
    pattern = rf"^ {{{indent}}}(?:{re.escape(key)}|'{re.escape(key)}'|\"{re.escape(key)}\")\s*:\s*$"
    starts = [index for index, line in enumerate(lines) if re.match(pattern, line)]
    if len(starts) != 1:
        raise SecurityValidationError(f"workflow must contain exactly one {label}")
    start = starts[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].lstrip()
        current_indent = len(lines[index]) - len(stripped)
        if stripped and not stripped.startswith("#") and current_indent <= indent:
            end = index
            break
    return "\n".join(lines[start:end])


def _extract_claude_args(review_step: str) -> str:
    lines = review_step.splitlines()
    declarations = [index for index, line in enumerate(lines) if re.match(r"""^\s*(?:claude_args|'claude_args'|"claude_args")\s*:""", line)]
    if len(declarations) != 1:
        raise SecurityValidationError("LLM step must declare claude_args exactly once")
    starts = [index for index in declarations if lines[index].strip() == "claude_args: |"]
    if len(starts) != 1:
        raise SecurityValidationError("LLM step claude_args must use one literal block")
    start = starts[0]
    indent = len(lines[start]) - len(lines[start].lstrip())
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        body.append(line.strip())
    return "\n".join(body)


def _single_step_value(step: str, key: str, indent: int) -> str:
    key_pattern = rf"^ {{{indent}}}(?:{re.escape(key)}|'(?:{re.escape(key)})'|\"(?:{re.escape(key)})\")\s*:\s*(.*)$"
    matches = [match.group(1).strip() for line in step.splitlines() if (match := re.match(key_pattern, line))]
    if len(matches) != 1 or not matches[0]:
        raise SecurityValidationError(f"LLM step must set {key} exactly once")
    return matches[0]


def _quoted_flag_value(block: str, flag: str) -> str:
    matches = re.findall(rf"(?m)^\s*{re.escape(flag)}\s+\"([^\"]*)\"\s*$", block)
    if len(matches) != 1:
        raise SecurityValidationError(f"claude_args must contain exactly one quoted {flag}")
    return matches[0]


def _plain_flag_value(block: str, flag: str) -> str:
    matches = re.findall(rf"(?m)^\s*{re.escape(flag)}\s+(\S+)\s*$", block)
    if len(matches) != 1:
        raise SecurityValidationError(f"claude_args must contain exactly one {flag}")
    return matches[0]


def _validate_claude_argument_surface(block: str) -> None:
    try:
        tokens = shlex.split(block, posix=True)
    except ValueError as exc:
        raise SecurityValidationError("claude_args is not valid shell-style argument text") from exc
    value_flags = set(EXPECTED_CLAUDE_FLAGS) - {"--strict-mcp-config"}
    observed: list[str] = []
    index = 0
    while index < len(tokens):
        flag = tokens[index]
        if flag == "--strict-mcp-config":
            observed.append(flag)
            index += 1
            continue
        if flag not in value_flags or index + 1 >= len(tokens) or tokens[index + 1].startswith("-"):
            raise SecurityValidationError(f"unexpected or malformed Claude argument: {flag}")
        observed.append(flag)
        index += 2
    if tuple(observed) != EXPECTED_CLAUDE_FLAGS:
        raise SecurityValidationError("Claude argument surface or ordering drifted")


def validate_workflow(path: Path) -> None:
    workflow = _read_regular_text(path, "agent-review workflow")
    oauth_lines = tuple(line.strip() for line in workflow.splitlines() if "CLAUDE_CODE_OAUTH_TOKEN" in line)
    if oauth_lines != EXPECTED_OAUTH_LINES:
        raise SecurityValidationError("workflow OAuth credential exposure drifted")
    forbidden_token_lines = tuple(line.strip() for line in workflow.splitlines() if "FORBIDDEN_CLAUDE_TOKEN" in line)
    if forbidden_token_lines != EXPECTED_FORBIDDEN_TOKEN_LINES:
        raise SecurityValidationError("structured-output credential handling drifted")
    jobs = _extract_mapping_block(workflow, "jobs", 0, "jobs mapping")
    review_job = _extract_mapping_block(jobs, "review", 2, "review job")
    if _single_step_value(review_job, "runs-on", 4) != EXPECTED_REVIEW_RUNNER:
        raise SecurityValidationError("review job runner boundary drifted")
    permissions = _extract_mapping_block(review_job, "permissions", 4, "review permissions mapping")
    permission_entries = tuple(line.strip() for line in permissions.splitlines()[1:] if line.strip() and not line.lstrip().startswith("#"))
    if permission_entries != ("contents: read", "pull-requests: read", "issues: read"):
        raise SecurityValidationError("review job permissions must remain read-only")
    review_environment = _extract_mapping_block(review_job, "env", 4, "review environment mapping")
    if _single_step_value(review_environment, "CLAUDE_CODE_SUBPROCESS_ENV_SCRUB", 6) != '"0"':
        raise SecurityValidationError("host action subprocess setup boundary drifted")
    if _single_step_value(review_environment, "ANTHROPIC_API_KEY", 6) != '""':
        raise SecurityValidationError("ambient Anthropic API key must remain cleared")
    if _single_step_value(review_environment, "ANTHROPIC_AUTH_TOKEN", 6) != '""':
        raise SecurityValidationError("ambient Anthropic auth token must remain cleared")

    prepare_step = _extract_step(review_job, "Prepare isolated Claude runtime")
    if "CLAUDE_CODE_OAUTH_TOKEN" in prepare_step:
        raise SecurityValidationError("Claude install/version preparation must be credential-free")

    review_step = _extract_step(review_job, "LLM first-pass review")
    review_lines = review_step.splitlines()
    step_indent = len(review_lines[0]) - len(review_lines[0].lstrip())
    if _single_step_value(review_step, "id", step_indent + 2) != "review_agent":
        raise SecurityValidationError("LLM step identity drifted")
    if _single_step_value(review_step, "if", step_indent + 2) != "steps.gate.outputs.ok == 'true'":
        raise SecurityValidationError("LLM step gate drifted")
    if _single_step_value(review_step, "uses", step_indent + 2) != EXPECTED_ACTION:
        raise SecurityValidationError("LLM action pin drifted")
    with_pattern = rf"^ {{{step_indent + 2}}}(?:with|'with'|\"with\")\s*:"
    with_lines = [line for line in review_lines if re.match(with_pattern, line)]
    if len(with_lines) != 1 or with_lines[0] != " " * (step_indent + 2) + "with:":
        raise SecurityValidationError("LLM step must contain exactly one with mapping")
    if _single_step_value(review_step, "path_to_claude_code_executable", step_indent + 4) != EXPECTED_WRAPPER_INPUT:
        raise SecurityValidationError("LLM action must execute through the Bubblewrap launcher")
    if _single_step_value(review_step, "claude_code_oauth_token", step_indent + 4) != EXPECTED_OAUTH_INPUT:
        raise SecurityValidationError("LLM action OAuth input drifted")
    output_step = _extract_step(review_job, "Validate structured review output")
    output_lines = output_step.splitlines()
    output_indent = len(output_lines[0]) - len(output_lines[0].lstrip())
    if _single_step_value(output_step, "FORBIDDEN_CLAUDE_TOKEN", output_indent + 4) != EXPECTED_OAUTH_INPUT:
        raise SecurityValidationError("structured-output token check drifted")
    capture = "forbidden_claude_token=$FORBIDDEN_CLAUDE_TOKEN"
    scrub = "unset FORBIDDEN_CLAUDE_TOKEN"
    local_check = "&& comment_excludes_forbidden_token"
    python_validation = '"$REVIEW_PYTHON" .github/scripts/validate_agent_review_comment.py'
    for fragment in (capture, scrub, local_check, python_validation):
        if output_step.count(fragment) != 1:
            raise SecurityValidationError(f"structured-output credential isolation is missing: {fragment}")
    if not output_step.index(capture) < output_step.index(scrub) < output_step.index(local_check) < output_step.index(python_validation):
        raise SecurityValidationError("structured-output credential isolation order drifted")
    args = _extract_claude_args(review_step)
    _validate_claude_argument_surface(args)
    if _quoted_flag_value(args, "--tools") != EXPECTED_TOOLS:
        raise SecurityValidationError("Claude tool families must remain exactly Read,Skill")
    if _quoted_flag_value(args, "--allowedTools") != ",".join(EXPECTED_ALLOW):
        raise SecurityValidationError("Claude allowedTools drifted from the managed policy")
    if _quoted_flag_value(args, "--disallowedTools") != ",".join(EXPECTED_DENY):
        raise SecurityValidationError("Claude disallowedTools drifted from the managed policy")
    if _plain_flag_value(args, "--permission-mode") != "dontAsk":
        raise SecurityValidationError("Claude permission mode must remain dontAsk")
    if _plain_flag_value(args, "--setting-sources") != "user,project":
        raise SecurityValidationError("Claude setting sources drifted")
    if len(re.findall(r"(?m)^\s*--strict-mcp-config\s*$", args)) != 1:
        raise SecurityValidationError("Claude must use strict MCP configuration")


def _expect(value: Any, expected: Any, label: str) -> None:
    if value != expected:
        raise SecurityValidationError(f"managed setting {label} drifted")


def validate_managed_settings(path: Path) -> None:
    raw = _read_regular_text(path, "Claude managed policy")
    try:
        settings = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SecurityValidationError("Claude managed policy is not valid JSON") from exc
    if not isinstance(settings, dict):
        raise SecurityValidationError("Claude managed policy must be a JSON object")
    expected_top_level_keys = {
        "$schema",
        "permissions",
        "allowManagedPermissionRulesOnly",
        "allowedMcpServers",
        "allowManagedMcpServersOnly",
        "allowManagedHooksOnly",
        "disableAllHooks",
        "disableSkillShellExecution",
        "disableSideloadFlags",
        "disableClaudeAiConnectors",
        "disableRemoteControl",
        "disableArtifact",
    }
    _expect(set(settings), expected_top_level_keys, "top-level keys")
    permissions = settings.get("permissions")
    if not isinstance(permissions, dict):
        raise SecurityValidationError("Claude managed policy has no permissions object")
    _expect(
        set(permissions),
        {"defaultMode", "allow", "ask", "deny", "disableBypassPermissionsMode", "disableAutoMode"},
        "permissions keys",
    )

    _expect(permissions.get("defaultMode"), "dontAsk", "permissions.defaultMode")
    _expect(permissions.get("allow"), list(EXPECTED_ALLOW), "permissions.allow")
    _expect(permissions.get("ask"), [], "permissions.ask")
    _expect(permissions.get("deny"), list(EXPECTED_DENY), "permissions.deny")
    _expect(
        permissions.get("disableBypassPermissionsMode"),
        "disable",
        "permissions.disableBypassPermissionsMode",
    )
    _expect(permissions.get("disableAutoMode"), "disable", "permissions.disableAutoMode")

    required_true = (
        "allowManagedPermissionRulesOnly",
        "allowManagedMcpServersOnly",
        "allowManagedHooksOnly",
        "disableAllHooks",
        "disableSkillShellExecution",
        "disableSideloadFlags",
        "disableClaudeAiConnectors",
        "disableRemoteControl",
        "disableArtifact",
    )
    for key in required_true:
        _expect(settings.get(key), True, key)
    _expect(settings.get("allowedMcpServers"), [], "allowedMcpServers")


def validate_wrapper(path: Path) -> None:
    wrapper = _read_regular_text(path, "Claude Bubblewrap launcher")
    required_fragments = (
        "/etc/claude-code/managed-settings.json",
        "/opt/claude-egress-proxy.py",
        '/usr/bin/python3 -I "$workspace/.github/scripts/validate_agent_review_security.py"',
        '/usr/bin/python3 -I "$workspace/.github/scripts/claude_egress_proxy.py"',
        "/usr/bin/python3 -I /opt/claude-egress-proxy.py",
        "unset CLAUDE_CODE_OAUTH_TOKEN",
        'CLAUDE_CODE_OAUTH_TOKEN="$oauth_token" bwrap',
        "serve --socket",
        "relay --socket",
        "--setenv HTTPS_PROXY http://127.0.0.1:3128",
        "--setenv HTTP_PROXY http://127.0.0.1:3128",
        "--setenv CLAUDE_CODE_SUBPROCESS_ENV_SCRUB 1",
        "--setenv CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC 1",
    )
    for fragment in required_fragments:
        if fragment not in wrapper:
            raise SecurityValidationError(f"Bubblewrap launcher is missing invariant: {fragment}")
    if len(re.findall(r"(?m)^\s*--unshare-net\s*$", wrapper)) != 1:
        raise SecurityValidationError("Bubblewrap launcher must unshare exactly one network namespace")
    if "--share-net" in wrapper:
        raise SecurityValidationError("Bubblewrap launcher must never rejoin the host network namespace")
    oauth_exports = re.findall(r"(?m)^\s*CLAUDE_CODE_OAUTH_TOKEN=.*$", wrapper)
    if oauth_exports != ['CLAUDE_CODE_OAUTH_TOKEN="$oauth_token" bwrap "${bwrap_args[@]}" \\']:
        raise SecurityValidationError("OAuth credential must enter only the final Bubblewrap process")
    if "/etc/resolv.conf" in wrapper:
        raise SecurityValidationError("network-isolated sandbox must not receive host DNS configuration")


def _literal_assignment(module: ast.Module, name: str) -> Any:
    values: list[ast.expr] = []
    for statement in module.body:
        if isinstance(statement, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in statement.targets):
            values.append(statement.value)
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name) and statement.target.id == name:
            values.append(statement.value)
    if len(values) != 1:
        raise SecurityValidationError(f"egress proxy must assign {name} exactly once")
    value = values[0]
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "frozenset"
        and len(value.args) == 1
        and not value.keywords
    ):
        value = value.args[0]
        try:
            return frozenset(ast.literal_eval(value))
        except (TypeError, ValueError) as exc:
            raise SecurityValidationError(f"egress proxy {name} must be a literal frozenset") from exc
    try:
        return ast.literal_eval(value)
    except (TypeError, ValueError) as exc:
        raise SecurityValidationError(f"egress proxy {name} must be a literal") from exc


def validate_egress_proxy(path: Path) -> None:
    source = _read_regular_text(path, "Claude egress proxy")
    try:
        module = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SecurityValidationError("Claude egress proxy is not valid Python") from exc
    _expect(_literal_assignment(module, "ALLOWED_HOSTS"), EXPECTED_EGRESS_HOSTS, "egress hosts")
    _expect(_literal_assignment(module, "ALLOWED_PORT"), EXPECTED_EGRESS_PORT, "egress port")


def validate_repository(repo_root: Path) -> None:
    validate_workflow(repo_root / ".github/workflows/agent-review.yml")
    validate_managed_settings(repo_root / ".github/agent-review/managed-settings.json")
    validate_wrapper(repo_root / ".github/scripts/run_claude_in_bwrap.sh")
    validate_egress_proxy(repo_root / ".github/scripts/claude_egress_proxy.py")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    args = parser.parse_args(argv)
    try:
        validate_repository(args.repo_root.resolve())
    except SecurityValidationError as exc:
        print(f"agent-review security validation failed: {exc}", file=sys.stderr)
        return 1
    print("agent-review security boundary is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
