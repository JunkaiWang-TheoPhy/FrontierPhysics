#!/usr/bin/env python3
"""Behavioral tests for the dependency-free Claude egress proxy.

Run with:

    python3 .github/scripts/test_claude_egress_proxy.py
"""

from __future__ import annotations

import contextlib
import io
import os
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_egress_proxy as proxy

SCRIPT = Path(__file__).with_name("claude_egress_proxy.py")


def _read_through(stream: socket.socket, marker: bytes) -> tuple[bytes, bytes]:
    data = bytearray()
    while marker not in data:
        chunk = stream.recv(4096)
        if not chunk:
            raise AssertionError(f"connection closed before marker {marker!r}: {bytes(data)!r}")
        data.extend(chunk)
    boundary = data.index(marker) + len(marker)
    return bytes(data[:boundary]), bytes(data[boundary:])


def _read_all(stream: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = stream.recv(4096)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


class EchoServer:
    def __init__(self) -> None:
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(8)
        self.listener.settimeout(0.2)
        self.address = self.listener.getsockname()
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def __enter__(self) -> EchoServer:
        self.thread.start()
        return self

    def __exit__(self, *_unused: object) -> None:
        self.stop.set()
        self.listener.close()
        self.thread.join(timeout=2)

    def _serve(self) -> None:
        while not self.stop.is_set():
            try:
                client, _ = self.listener.accept()
            except socket.timeout:  # noqa: UP041  # Not an alias of TimeoutError on Python 3.8.
                continue
            except OSError:
                return
            threading.Thread(target=self._echo, args=(client,), daemon=True).start()

    @staticmethod
    def _echo(client: socket.socket) -> None:
        with client:
            while True:
                data = client.recv(4096)
                if not data:
                    with contextlib.suppress(OSError):
                        client.shutdown(socket.SHUT_WR)
                    return
                client.sendall(data)


class UnixProxyHarness:
    def __init__(self, directory: Path, connector: proxy.Connector) -> None:
        self.path = directory / "proxy.sock"
        self.listener, self.owned = proxy.create_unix_listener(self.path)
        self.stop = threading.Event()

        def handler(client: socket.socket) -> None:
            proxy.handle_proxy_client(client, connector)

        self.thread = threading.Thread(
            target=proxy.serve_connections,
            args=(self.listener, handler, self.stop),
            daemon=True,
        )

    def __enter__(self) -> UnixProxyHarness:
        self.thread.start()
        return self

    def __exit__(self, *_unused: object) -> None:
        self.stop.set()
        self.listener.close()
        self.thread.join(timeout=2)
        proxy.unlink_owned_path(self.owned)


@contextlib.contextmanager
def _connected_unix(path: Path) -> Iterator[socket.socket]:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.settimeout(3)
        client.connect(os.fspath(path))
        yield client
    finally:
        client.close()


class ConnectPolicyTests(unittest.TestCase):
    def test_exact_allowed_authorities(self) -> None:
        for authority, expected_host in (
            (b"api.anthropic.com:443", "api.anthropic.com"),
            (b"platform.claude.com:443", "platform.claude.com"),
            (b"API.ANTHROPIC.COM:443", "api.anthropic.com"),
        ):
            with self.subTest(authority=authority):
                request = proxy.parse_connect_request(
                    b"CONNECT " + authority + b" HTTP/1.1\r\nHost: " + authority + b"\r\n\r\n",
                    b"early bytes",
                )
                self.assertEqual((request.host, request.port), (expected_host, 443))
                self.assertEqual(request.early_data, b"early bytes")

    def test_disallowed_and_ambiguous_targets(self) -> None:
        targets = (
            b"api.anthropic.com:80",
            b"api.anthropic.com:0443",
            b"api.anthropic.com.:443",
            b"evil.api.anthropic.com:443",
            b"api.anthropic.com.evil.test:443",
            b"104.18.1.1:443",
            b"[::1]:443",
            b"user@api.anthropic.com:443",
            b"api.anthropic.com%00.evil:443",
            b"api.anthropic.com:443/",
            b"https://api.anthropic.com:443",
            b"api.anthropic.com",
            b"api.anthropic.com:443:443",
        )
        for target in targets:
            with self.subTest(target=target):
                with self.assertRaises(proxy.ConnectRequestError):
                    proxy.parse_connect_request(b"CONNECT " + target + b" HTTP/1.1\r\n\r\n")

    def test_non_connect_and_ambiguous_request_syntax_are_denied(self) -> None:
        requests = (
            b"GET api.anthropic.com:443 HTTP/1.1\r\n\r\n",
            b"connect api.anthropic.com:443 HTTP/1.1\r\n\r\n",
            b"CONNECT  api.anthropic.com:443 HTTP/1.1\r\n\r\n",
            b"CONNECT api.anthropic.com:443\tHTTP/1.1\r\n\r\n",
            b"CONNECT api.anthropic.com:443 HTTP/2\r\n\r\n",
            b"CONNECT api.anthropic.com:443 HTTP/1.1\n\n",
            b"CONNECT api.anthropic.com:443 HTTP/1.1\r\n folded: value\r\n\r\n",
            b"CONNECT api.anthropic.com:443 HTTP/1.1\r\nBad Header: value\r\n\r\n",
            b"CONNECT api.anthropic.com:443 HTTP/1.1\r\nX-Test: one\x00two\r\n\r\n",
            b"CONNECT api.anthropic.com:443 HTTP/1.1\r\nContent-Length: 0\r\n\r\n",
            b"CONNECT api.anthropic.com:443 HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n",
            b"CONNECT api.anthropic.com:443 HTTP/1.1\r\nHost: api.anthropic.com:443\r\nHost: api.anthropic.com:443\r\n\r\n",
            b"CONNECT api.anthropic.com:443 HTTP/1.1\r\nHost: platform.claude.com:443\r\n\r\n",
        )
        for request in requests:
            with self.subTest(request=request):
                with self.assertRaises(proxy.ConnectRequestError):
                    proxy.parse_connect_request(request)

    def test_oversized_and_incomplete_headers_are_denied(self) -> None:
        with self.assertRaises(proxy.ConnectRequestError):
            proxy.parse_connect_request(b"CONNECT api.anthropic.com:443 HTTP/1.1\r\n")
        oversized = b"CONNECT api.anthropic.com:443 HTTP/1.1\r\nX: " + b"a" * proxy.MAX_HEADER_BYTES + b"\r\n\r\n"
        with self.assertRaises(proxy.ConnectRequestError):
            proxy.parse_connect_request(oversized)

    def test_dns_resolution_cannot_target_a_special_use_address(self) -> None:
        resolution = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 443))]
        with mock.patch.object(socket, "getaddrinfo", return_value=resolution):
            with self.assertRaisesRegex(OSError, "no globally routable address"):
                proxy._default_connector("api.anthropic.com", 443)


@unittest.skipUnless(hasattr(socket, "AF_UNIX"), "Unix sockets are required")
class StreamingIntegrationTests(unittest.TestCase):
    def test_allowed_tunnel_streams_early_and_later_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, EchoServer() as echo:
            directory = Path(temporary)

            def connector(_host: str, _port: int) -> socket.socket:
                return socket.create_connection(echo.address, timeout=2)

            with UnixProxyHarness(directory, connector) as host_proxy, _connected_unix(host_proxy.path) as client:
                client.sendall(b"CONNECT api.anthropic.com:443 HTTP/1.1\r\nHost: api.anthropic.com:443\r\n\r\nearly-")
                response, tunneled = _read_through(client, b"\r\n\r\n")
                self.assertTrue(response.startswith(b"HTTP/1.1 200 "), response)
                client.sendall(b"later")
                client.shutdown(socket.SHUT_WR)
                tunneled += _read_all(client)
                self.assertEqual(tunneled, b"early-later")

    def test_denied_target_never_invokes_connector(self) -> None:
        called = threading.Event()

        def forbidden_connector(_host: str, _port: int) -> socket.socket:
            called.set()
            raise AssertionError("policy denial reached the network connector")

        with tempfile.TemporaryDirectory() as temporary:
            with UnixProxyHarness(Path(temporary), forbidden_connector) as host_proxy, _connected_unix(host_proxy.path) as client:
                client.sendall(b"CONNECT 127.0.0.1:443 HTTP/1.1\r\n\r\n")
                response = _read_all(client)
            self.assertTrue(response.startswith(b"HTTP/1.1 403 "), response)
            self.assertFalse(called.is_set())

    def test_tcp_loopback_relay_reaches_unix_proxy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, EchoServer() as echo:
            directory = Path(temporary)

            def connector(_host: str, _port: int) -> socket.socket:
                return socket.create_connection(echo.address, timeout=2)

            with UnixProxyHarness(directory, connector) as host_proxy:
                listener = proxy.create_loopback_listener("127.0.0.1", 0)
                stop = threading.Event()

                def handler(client: socket.socket) -> None:
                    proxy.handle_relay_client(client, host_proxy.path)

                thread = threading.Thread(
                    target=proxy.serve_connections,
                    args=(listener, handler, stop),
                    daemon=True,
                )
                thread.start()
                try:
                    with socket.create_connection(listener.getsockname(), timeout=2) as client:
                        client.settimeout(3)
                        client.sendall(b"CONNECT platform.claude.com:443 HTTP/1.1\r\n\r\nrelay-data")
                        response, tunneled = _read_through(client, b"\r\n\r\n")
                        self.assertTrue(response.startswith(b"HTTP/1.1 200 "), response)
                        client.shutdown(socket.SHUT_WR)
                        tunneled += _read_all(client)
                        self.assertEqual(tunneled, b"relay-data")
                finally:
                    stop.set()
                    listener.close()
                    thread.join(timeout=2)

    def test_relay_closes_connection_when_host_proxy_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            sandbox_client, relay_client = socket.socketpair()

            def run_relay() -> None:
                with relay_client:
                    proxy.handle_relay_client(relay_client, Path(temporary) / "missing.sock")

            thread = threading.Thread(target=run_relay, daemon=True)
            thread.start()
            with sandbox_client:
                sandbox_client.settimeout(2)
                with contextlib.suppress(BrokenPipeError):
                    sandbox_client.sendall(b"CONNECT api.anthropic.com:443 HTTP/1.1\r\n\r\n")
                try:
                    received = sandbox_client.recv(1)
                except ConnectionResetError:
                    received = b""
                self.assertEqual(received, b"")
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())

    def test_listener_caps_concurrent_connections(self) -> None:
        listener = proxy.create_loopback_listener("127.0.0.1", 0)
        stop = threading.Event()
        entered = threading.Event()
        release = threading.Event()

        def blocking_handler(_client: socket.socket) -> None:
            entered.set()
            release.wait(timeout=3)

        thread = threading.Thread(
            target=proxy.serve_connections,
            args=(listener, blocking_handler, stop, 1),
            daemon=True,
        )
        thread.start()
        first = socket.create_connection(listener.getsockname(), timeout=2)
        second: socket.socket | None = None
        try:
            self.assertTrue(entered.wait(timeout=2))
            second = socket.create_connection(listener.getsockname(), timeout=2)
            second.settimeout(2)
            self.assertEqual(second.recv(1), b"")
        finally:
            if second is not None:
                second.close()
            first.close()
            release.set()
            stop.set()
            listener.close()
            thread.join(timeout=2)

    def test_listener_handles_pre_python_310_socket_timeout(self) -> None:
        class LegacySocketTimeout(OSError):
            pass

        stop = threading.Event()
        listener = mock.Mock()

        def accept() -> None:
            if listener.accept.call_count == 1:
                raise LegacySocketTimeout
            stop.set()
            raise OSError

        listener.accept.side_effect = accept
        with mock.patch.object(proxy.socket, "timeout", LegacySocketTimeout):
            proxy.serve_connections(listener, lambda _client: None, stop)
        self.assertEqual(listener.accept.call_count, 2)

    @unittest.skipUnless(os.name == "posix", "mode and POSIX signal lifecycle test")
    def test_serve_cli_publishes_mode_0600_then_cleans_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            socket_path = directory / "serve.sock"
            ready_path = directory / "ready"
            process = subprocess.Popen(
                [
                    sys.executable,
                    os.fspath(SCRIPT),
                    "serve",
                    "--socket",
                    os.fspath(socket_path),
                    "--ready-file",
                    os.fspath(ready_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                deadline = time.monotonic() + 5
                while not ready_path.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    self.fail(f"serve exited before readiness: stdout={stdout!r}, stderr={stderr!r}")
                self.assertTrue(ready_path.exists())
                self.assertTrue(stat.S_ISSOCK(socket_path.lstat().st_mode))
                self.assertEqual(stat.S_IMODE(socket_path.lstat().st_mode), 0o600)
                process.send_signal(signal.SIGTERM)
                process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate()
            self.assertFalse(socket_path.exists())
            self.assertFalse(ready_path.exists())

    @unittest.skipUnless(os.name == "posix", "relay ownership checks and child process groups are POSIX-only")
    def test_relay_launches_child_with_proxy_environment_and_returns_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, EchoServer() as echo:
            directory = Path(temporary)

            def connector(_host: str, _port: int) -> socket.socket:
                return socket.create_connection(echo.address, timeout=2)

            with UnixProxyHarness(directory, connector) as host_proxy:
                child_code = (
                    "import os,sys; "
                    "url=os.environ.get('HTTPS_PROXY',''); "
                    "sys.exit(7 if url.startswith('http://127.0.0.1:') and os.environ.get('NO_PROXY') == '' else 9)"
                )
                return_code = proxy.run_relay(
                    host_proxy.path,
                    "127.0.0.1",
                    0,
                    [sys.executable, "-c", child_code],
                )
                self.assertEqual(return_code, 7)


class CliPolicyTests(unittest.TestCase):
    def test_relay_cli_rejects_non_loopback_and_invalid_ports(self) -> None:
        parser = proxy.build_parser()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["relay", "--socket", "x", "--listen-host", "0.0.0.0", "--", "true"])
            with self.assertRaises(SystemExit):
                parser.parse_args(["relay", "--socket", "x", "--listen-port", "0", "--", "true"])
            with self.assertRaises(SystemExit):
                parser.parse_args(["relay", "--socket", "x", "--listen-port", "65536", "--", "true"])

    def test_relay_requires_command(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                proxy.main(["relay", "--socket", "missing.sock", "--"])


if __name__ == "__main__":
    unittest.main()
