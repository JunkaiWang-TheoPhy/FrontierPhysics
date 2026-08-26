#!/usr/bin/env python3
"""Linux integration tests for the complete agent-review Bubblewrap launcher."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
WRAPPER = Path(".github/scripts/run_claude_in_bwrap.sh")
RUN_ID = "987654321"
RUN_ATTEMPT = "1"
OAUTH_SENTINEL = "test-oauth-sentinel"

FAKE_CLAUDE = r"""#!/usr/bin/python3
import os
import socket
import sys
from pathlib import Path


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(1)


if sys.argv[1:] == ["--version"]:
    if "CLAUDE_CODE_OAUTH_TOKEN" in os.environ:
        fail("version probe inherited OAuth")
    print("2.1.246-integration")
    raise SystemExit(0)

if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") != "test-oauth-sentinel":
    fail("review did not receive the OAuth sentinel")
if "UNSAFE_HOST_CANARY" in os.environ:
    fail("host environment was not scrubbed")
if os.environ.get("CLAUDE_CODE_SUBPROCESS_ENV_SCRUB") != "1":
    fail("Claude subprocess scrubbing is disabled")
if os.environ.get("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC") != "1":
    fail("nonessential Claude traffic is enabled")
if os.environ.get("HTTPS_PROXY") != "http://127.0.0.1:3128":
    fail("HTTPS proxy is not the loopback relay")
if os.environ.get("NO_PROXY") != "" or "ALL_PROXY" in os.environ:
    fail("proxy bypass environment survived")
if Path("/etc/resolv.conf").exists():
    fail("host DNS configuration is mounted")

managed_policy = Path("/etc/claude-code/managed-settings.json")
if not managed_policy.is_file():
    fail("managed policy is not mounted")
try:
    managed_policy.open("ab").close()
except OSError:
    pass
else:
    fail("managed policy is writable")


def expect_unreachable(address):
    family = socket.AF_INET6 if ":" in address[0] else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as stream:
        stream.settimeout(0.5)
        try:
            stream.connect(address)
        except OSError:
            return
    fail("direct network destination was reachable: " + repr(address))


expect_unreachable(("1.1.1.1", 443))
expect_unreachable(("169.254.169.254", 80))
expect_unreachable(("2606:4700:4700::1111", 443))
try:
    socket.getaddrinfo("example.com", 443)
except socket.gaierror:
    pass
else:
    fail("sandbox unexpectedly resolved public DNS")


def connect_request(authority):
    with socket.create_connection(("127.0.0.1", 3128), timeout=3) as stream:
        stream.sendall(b"CONNECT " + authority + b" HTTP/1.1\r\nHost: " + authority + b"\r\n\r\n")
        stream.settimeout(5)
        response = bytearray()
        while b"\r\n\r\n" not in response:
            chunk = stream.recv(4096)
            if not chunk:
                break
            response.extend(chunk)
        return bytes(response)


denied = connect_request(b"example.com:443")
if not denied.startswith(b"HTTP/1.1 403 "):
    fail("disallowed CONNECT was not denied: " + repr(denied))

if "--live-egress" in sys.argv[1:]:
    allowed = connect_request(b"api.anthropic.com:443")
    if not allowed.startswith(b"HTTP/1.1 200 "):
        fail("allowed Anthropic CONNECT did not succeed: " + repr(allowed))

print("review-ok")
"""


@unittest.skipUnless(sys.platform.startswith("linux"), "Bubblewrap integration is Linux-only")
class BubblewrapLauncherIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bwrap = shutil.which("bwrap")
        if self.bwrap is None:
            self.skipTest("bwrap is unavailable")
        probe = subprocess.run(
            [
                self.bwrap,
                "--die-with-parent",
                "--unshare-user",
                "--unshare-net",
                "--ro-bind",
                "/",
                "/",
                "/usr/bin/true",
            ],
            capture_output=True,
            check=False,
            timeout=10,
        )
        if probe.returncode != 0:
            self.skipTest(f"bwrap user/network namespaces are unavailable: {probe.stderr.decode(errors='replace').strip()}")

        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        self.runner_temp = self.root / "runner"
        self.workspace.mkdir()
        self.runner_temp.mkdir()
        self._create_fixture()

    def tearDown(self) -> None:
        if hasattr(self, "temporary"):
            self.temporary.cleanup()

    def _copy(self, relative: str) -> None:
        source = REPO_ROOT / relative
        destination = self.workspace / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    def _create_fixture(self) -> None:
        for relative in (
            ".github/agent-review/managed-settings.json",
            ".github/scripts/claude_egress_proxy.py",
            ".github/scripts/run_claude_in_bwrap.sh",
            ".github/scripts/validate_agent_review_security.py",
            ".github/workflows/agent-review.yml",
            "CONTRIBUTING.md",
            "taxonomy.md",
        ):
            self._copy(relative)
        (self.workspace / WRAPPER).chmod(0o755)
        for relative in (".agents/skills/task-review", "pr-head", "pr-head-scripts-as-submitted"):
            (self.workspace / relative).mkdir(parents=True)
        for relative in (
            "changed_files.json",
            "review_files.json",
            "pr_meta.json",
            "advisory_checks.txt",
            "ai_detection.json",
        ):
            (self.workspace / relative).touch()

        self.claude_root = self.runner_temp / f"claude-cli-{RUN_ID}-{RUN_ATTEMPT}"
        self.agent_home = self.runner_temp / f"claude-home-{RUN_ID}-{RUN_ATTEMPT}"
        fake_cli = self.claude_root / "node_modules/@anthropic-ai/claude-code/bin/claude.exe"
        fake_cli.parent.mkdir(parents=True)
        fake_cli.write_text(textwrap.dedent(FAKE_CLAUDE), encoding="utf-8")
        fake_cli.chmod(0o755)
        self.agent_home.mkdir()

    def _environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "GITHUB_WORKSPACE": os.fspath(self.workspace),
                "RUNNER_TEMP": os.fspath(self.runner_temp),
                "GITHUB_RUN_ID": RUN_ID,
                "GITHUB_RUN_ATTEMPT": RUN_ATTEMPT,
                "SANDBOX_CLAUDE_ROOT": os.fspath(self.claude_root),
                "SANDBOX_AGENT_HOME": os.fspath(self.agent_home),
                "CLAUDE_CODE_OAUTH_TOKEN": OAUTH_SENTINEL,
                "UNSAFE_HOST_CANARY": "must-not-enter-sandbox",
            }
        )
        return environment

    def _run_wrapper(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = self._environment()
        return subprocess.run(
            [os.fspath(self.workspace / WRAPPER), *arguments],
            cwd=self.workspace,
            env=environment,
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )

    def test_version_is_credential_free_and_network_isolated(self) -> None:
        result = self._run_wrapper("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "2.1.246-integration")

    def test_review_uses_only_the_loopback_allowlist_relay(self) -> None:
        result = self._run_wrapper("--integration-test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "review-ok")
        self.assertFalse((self.runner_temp / f"ce-{RUN_ID}-{RUN_ATTEMPT}").exists())

    @unittest.skipUnless(os.environ.get("AGENT_REVIEW_LIVE_EGRESS_TEST") == "1", "live Anthropic connection is opt-in")
    def test_allowed_anthropic_connect_reaches_the_public_service(self) -> None:
        result = self._run_wrapper("--live-egress")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "review-ok")


if __name__ == "__main__":
    unittest.main()
