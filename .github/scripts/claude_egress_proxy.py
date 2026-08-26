#!/usr/bin/env python3
"""Small, fail-closed egress proxy used by the Claude review sandbox.

``serve`` runs outside Bubblewrap and accepts HTTP CONNECT requests on a Unix
socket.  It will only open TLS tunnels to the two Claude service authorities.
``relay`` runs inside Bubblewrap's network namespace, exposes that Unix socket
as a loopback HTTP proxy, and supervises the supplied command.

The implementation intentionally uses only the Python standard library so the
security boundary does not acquire a package-install or dependency surface.
"""

from __future__ import annotations

import argparse
import contextlib
import ipaddress
import os
import re
import signal
import socket
import stat
import subprocess
import sys
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import FrameType

ALLOWED_HOSTS = frozenset({"api.anthropic.com", "platform.claude.com"})
ALLOWED_PORT = 443
MAX_HEADER_BYTES = 64 * 1024
HEADER_TIMEOUT_SECONDS = 10.0
CONNECT_TIMEOUT_SECONDS = 15.0
BUFFER_SIZE = 64 * 1024
MAX_ACTIVE_CONNECTIONS = 32

_AUTHORITY_RE = re.compile(rb"([A-Za-z0-9.-]+):([0-9]+)\Z")
_HEADER_NAME_RE = re.compile(rb"[!#$%&'*+\-.^_`|~0-9A-Za-z]+\Z")

Connector = Callable[[str, int], socket.socket]
ConnectionHandler = Callable[[socket.socket], None]


class ConnectRequestError(ValueError):
    """An HTTP request that must not be proxied."""

    def __init__(self, status: int, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


@dataclass(frozen=True)
class ConnectRequest:
    host: str
    port: int
    early_data: bytes = b""


@dataclass(frozen=True)
class OwnedPath:
    """Identity of a path created by this process, for race-safe cleanup."""

    path: Path
    device: int
    inode: int


def _parse_authority(value: bytes) -> tuple[str, int]:
    """Parse and enforce the complete CONNECT allowlist in one operation."""

    match = _AUTHORITY_RE.fullmatch(value)
    if match is None:
        raise ConnectRequestError(403, "CONNECT authority is not allowed")

    host_bytes, port_bytes = match.groups()
    try:
        host = host_bytes.decode("ascii").lower()
    except UnicodeDecodeError as exc:  # Defensive; the regular expression is ASCII-only.
        raise ConnectRequestError(403, "CONNECT authority is not allowed") from exc

    # Compare the port's exact spelling too: variants such as 0443 are rejected
    # rather than normalized into an allowed authority.
    if host not in ALLOWED_HOSTS or port_bytes != b"443":
        raise ConnectRequestError(403, "CONNECT authority is not allowed")
    return host, ALLOWED_PORT


def parse_connect_request(header: bytes, early_data: bytes = b"") -> ConnectRequest:
    """Strictly parse one complete HTTP CONNECT header.

    The caller supplies exactly the bytes through the first CRLFCRLF.  Bytes
    already received after that boundary are carried as early tunnel data.
    """

    if len(header) > MAX_HEADER_BYTES:
        raise ConnectRequestError(431, "request header is too large")
    if not header.endswith(b"\r\n\r\n"):
        raise ConnectRequestError(400, "request header is incomplete")

    without_delimiter = header[:-4]
    # Reject bare CR/LF and obs-fold rather than letting two HTTP parsers assign
    # different meanings to the same byte stream.
    if b"\r" in without_delimiter.replace(b"\r\n", b"") or b"\n" in without_delimiter.replace(b"\r\n", b""):
        raise ConnectRequestError(400, "request uses invalid line endings")

    lines = without_delimiter.split(b"\r\n")
    if not lines or not lines[0]:
        raise ConnectRequestError(400, "request line is missing")
    request_parts = lines[0].split(b" ")
    if len(request_parts) != 3 or any(not part for part in request_parts):
        raise ConnectRequestError(400, "request line is malformed")

    method, authority, version = request_parts
    if method != b"CONNECT":
        raise ConnectRequestError(405, "only CONNECT is supported")
    if version not in {b"HTTP/1.0", b"HTTP/1.1"}:
        raise ConnectRequestError(400, "unsupported HTTP version")

    host, port = _parse_authority(authority)
    host_headers: list[bytes] = []
    for line in lines[1:]:
        if not line or line[:1] in {b" ", b"\t"} or b":" not in line:
            raise ConnectRequestError(400, "request header line is malformed")
        name, value = line.split(b":", 1)
        if _HEADER_NAME_RE.fullmatch(name) is None:
            raise ConnectRequestError(400, "request header name is malformed")
        if any((byte < 32 and byte != 9) or byte == 127 for byte in value):
            raise ConnectRequestError(400, "request header value contains control bytes")

        lower_name = name.lower()
        if lower_name in {b"content-length", b"transfer-encoding"}:
            raise ConnectRequestError(400, "CONNECT request body framing is not allowed")
        if lower_name == b"host":
            host_headers.append(value.strip(b" \t"))

    if len(host_headers) > 1:
        raise ConnectRequestError(400, "duplicate Host header")
    if host_headers:
        header_host, header_port = _parse_authority(host_headers[0])
        if (header_host, header_port) != (host, port):
            raise ConnectRequestError(400, "Host header does not match CONNECT authority")

    return ConnectRequest(host=host, port=port, early_data=early_data)


def read_connect_request(client: socket.socket) -> ConnectRequest:
    """Read one bounded HTTP header without dropping pipelined tunnel bytes."""

    data = bytearray()
    while True:
        delimiter = data.find(b"\r\n\r\n")
        if delimiter >= 0:
            header_end = delimiter + 4
            if header_end > MAX_HEADER_BYTES:
                raise ConnectRequestError(431, "request header is too large")
            return parse_connect_request(bytes(data[:header_end]), bytes(data[header_end:]))
        if len(data) >= MAX_HEADER_BYTES:
            raise ConnectRequestError(431, "request header is too large")
        chunk = client.recv(min(16 * 1024, MAX_HEADER_BYTES + 4 - len(data)))
        if not chunk:
            raise ConnectRequestError(400, "client closed before sending a complete request")
        data.extend(chunk)


def _default_connector(host: str, port: int) -> socket.socket:
    # Resolve once, reject special-use destinations, and connect to the vetted
    # numeric result. This prevents a poisoned resolver response from turning
    # an allowed hostname into access to runner-local or metadata services.
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    last_error: OSError | None = None
    for family, socket_type, protocol, _canonical_name, address in addresses:
        try:
            resolved = ipaddress.ip_address(address[0].split("%", 1)[0])
        except ValueError:
            continue
        if not resolved.is_global:
            continue
        upstream = socket.socket(family, socket_type, protocol)
        upstream.settimeout(CONNECT_TIMEOUT_SECONDS)
        try:
            upstream.connect(address)
        except OSError as exc:
            last_error = exc
            upstream.close()
            continue
        upstream.settimeout(None)
        return upstream
    if last_error is not None:
        raise OSError("all globally routable upstream addresses failed") from last_error
    raise OSError("upstream hostname has no globally routable address")


def _send_response(client: socket.socket, status: int, reason: str) -> None:
    safe_reason = reason.encode("ascii", "replace")
    response = b"HTTP/1.1 " + str(status).encode("ascii") + b" " + safe_reason + b"\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
    with contextlib.suppress(OSError):
        client.sendall(response)


def _abort_pair(first: socket.socket, second: socket.socket) -> None:
    for stream in (first, second):
        with contextlib.suppress(OSError):
            stream.shutdown(socket.SHUT_RDWR)


def _pump(source: socket.socket, destination: socket.socket) -> None:
    try:
        while True:
            chunk = source.recv(BUFFER_SIZE)
            if not chunk:
                with contextlib.suppress(OSError):
                    destination.shutdown(socket.SHUT_WR)
                return
            destination.sendall(chunk)
    except OSError:
        _abort_pair(source, destination)


def bridge_streams(left: socket.socket, right: socket.socket, left_to_right: bytes = b"") -> None:
    """Copy a tunnel in both directions, preserving TCP half-close semantics."""

    if left_to_right:
        right.sendall(left_to_right)
    left_pump = threading.Thread(target=_pump, args=(left, right), daemon=True)
    left_pump.start()
    _pump(right, left)
    left_pump.join()


def handle_proxy_client(client: socket.socket, connector: Connector = _default_connector) -> None:
    """Authorize one CONNECT request and stream its tunnel."""

    client.settimeout(HEADER_TIMEOUT_SECONDS)
    try:
        request = read_connect_request(client)
    except ConnectRequestError as exc:
        _send_response(client, exc.status, exc.reason)
        return
    except (OSError, TimeoutError):
        _send_response(client, 408, "request timeout")
        return

    try:
        upstream = connector(request.host, request.port)
    except OSError:
        _send_response(client, 502, "upstream connection failed")
        return

    with upstream:
        client.settimeout(None)
        try:
            client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            bridge_streams(client, upstream, request.early_data)
        except OSError:
            _abort_pair(client, upstream)


def handle_relay_client(client: socket.socket, unix_socket: Path) -> None:
    """Bridge one sandbox loopback connection to the host Unix socket."""

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as host_proxy:
        try:
            host_proxy.connect(os.fspath(unix_socket))
            bridge_streams(client, host_proxy)
        except OSError:
            _abort_pair(client, host_proxy)


def _run_handler(handler: ConnectionHandler, client: socket.socket, slots: threading.BoundedSemaphore) -> None:
    with client:
        try:
            handler(client)
        except Exception as exc:  # Keep an individual malformed connection from stopping the listener.
            print(f"claude egress proxy connection failed: {type(exc).__name__}", file=sys.stderr)
        finally:
            slots.release()


def serve_connections(
    listener: socket.socket,
    handler: ConnectionHandler,
    stop: threading.Event,
    max_active_connections: int = MAX_ACTIVE_CONNECTIONS,
) -> None:
    """Accept connections until ``stop`` is set or the listener is closed."""

    if max_active_connections < 1:
        raise ValueError("max_active_connections must be positive")
    slots = threading.BoundedSemaphore(max_active_connections)
    listener.settimeout(0.2)
    while not stop.is_set():
        try:
            client, _ = listener.accept()
        except TimeoutError:
            continue
        except OSError:
            if stop.is_set():
                return
            raise
        if not slots.acquire(blocking=False):
            client.close()
            continue
        try:
            threading.Thread(target=_run_handler, args=(handler, client, slots), daemon=True).start()
        except BaseException:
            slots.release()
            client.close()
            raise


def _owned_path(path: Path) -> OwnedPath:
    metadata = path.lstat()
    return OwnedPath(path=path, device=metadata.st_dev, inode=metadata.st_ino)


def unlink_owned_path(owned: OwnedPath | None) -> None:
    """Remove a created path only if it is still the same filesystem object."""

    if owned is None:
        return
    try:
        current = owned.path.lstat()
    except FileNotFoundError:
        return
    if (current.st_dev, current.st_ino) == (owned.device, owned.inode):
        with contextlib.suppress(FileNotFoundError):
            owned.path.unlink()


def create_unix_listener(path: Path) -> tuple[socket.socket, OwnedPath]:
    """Create an exclusive, owner-only Unix listener."""

    path = path.absolute()
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to replace existing Unix socket path: {path}")

    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    old_umask = os.umask(0o177)
    try:
        listener.bind(os.fspath(path))
    except BaseException:
        listener.close()
        raise
    finally:
        os.umask(old_umask)

    owned: OwnedPath | None = None
    try:
        os.chmod(path, 0o600)
        metadata = path.lstat()
        if not stat.S_ISSOCK(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise PermissionError(f"Unix socket is not an owner-only socket: {path}")
        listener.listen(128)
        owned = _owned_path(path)
        return listener, owned
    except BaseException:
        listener.close()
        if owned is None:
            with contextlib.suppress(FileNotFoundError):
                path.unlink()
        else:
            unlink_owned_path(owned)
        raise


def create_ready_file(path: Path) -> OwnedPath:
    """Exclusively publish readiness with owner-only permissions."""

    path = path.absolute()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(b"ready\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        with contextlib.suppress(OSError):
            os.close(descriptor)
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
        raise
    return _owned_path(path)


def _verify_unix_socket(path: Path) -> None:
    metadata = path.lstat()
    if not stat.S_ISSOCK(metadata.st_mode):
        raise ValueError(f"relay target is not a Unix socket: {path}")
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise PermissionError(f"relay target must have mode 0600: {path}")
    if hasattr(os, "geteuid") and metadata.st_uid != os.geteuid():
        raise PermissionError(f"relay target is not owned by this user: {path}")


def create_loopback_listener(host: str, port: int) -> socket.socket:
    if host != "127.0.0.1":
        raise ValueError("relay listener must use IPv4 loopback 127.0.0.1")
    if not 0 <= port <= 65535:
        raise ValueError("relay port is outside the valid TCP range")
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind((host, port))
        listener.listen(128)
        return listener
    except BaseException:
        listener.close()
        raise


def _signals_to_handle() -> tuple[signal.Signals, ...]:
    names = ("SIGINT", "SIGTERM", "SIGHUP", "SIGQUIT")
    return tuple(getattr(signal, name) for name in names if hasattr(signal, name))


def _install_signal_handlers(
    handler: Callable[[int, FrameType | None], None],
) -> dict[signal.Signals, signal.Handlers]:
    previous: dict[signal.Signals, signal.Handlers] = {}
    for signum in _signals_to_handle():
        previous[signum] = signal.getsignal(signum)
        signal.signal(signum, handler)
    return previous


def _restore_signal_handlers(previous: dict[signal.Signals, signal.Handlers]) -> None:
    for signum, handler in previous.items():
        signal.signal(signum, handler)


def run_serve(socket_path: Path, ready_path: Path) -> int:
    stop = threading.Event()
    listener: socket.socket | None = None
    owned_socket: OwnedPath | None = None
    owned_ready: OwnedPath | None = None
    previous_handlers: dict[signal.Signals, signal.Handlers] = {}

    def request_stop(_signum: int, _frame: FrameType | None) -> None:
        stop.set()

    try:
        previous_handlers = _install_signal_handlers(request_stop)
        listener, owned_socket = create_unix_listener(socket_path)
        owned_ready = create_ready_file(ready_path)
        serve_connections(listener, handle_proxy_client, stop)
        return 0
    finally:
        stop.set()
        if listener is not None:
            listener.close()
        if previous_handlers:
            _restore_signal_handlers(previous_handlers)
        unlink_owned_path(owned_ready)
        unlink_owned_path(owned_socket)


def _child_environment(host: str, port: int) -> dict[str, str]:
    environment = os.environ.copy()
    proxy_url = f"http://{host}:{port}"
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        environment[name] = proxy_url
    for name in ("ALL_PROXY", "all_proxy"):
        environment.pop(name, None)
    # An inherited wildcard or Anthropic-specific bypass would silently escape
    # the relay.  The sandbox has no other network route, but fail closed here.
    environment["NO_PROXY"] = ""
    environment["no_proxy"] = ""
    return environment


def _forward_signal(process: subprocess.Popen[bytes], signum: int) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signum)
        else:
            process.send_signal(signum)
    except ProcessLookupError:
        pass


def _stop_child(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "posix":
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
    else:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait()


def run_relay(socket_path: Path, listen_host: str, listen_port: int, command: Sequence[str]) -> int:
    if not command:
        raise ValueError("relay requires a child command")
    socket_path = socket_path.absolute()
    _verify_unix_socket(socket_path)

    listener = create_loopback_listener(listen_host, listen_port)
    actual_port = int(listener.getsockname()[1])
    stop = threading.Event()

    def relay_handler(client: socket.socket) -> None:
        handle_relay_client(client, socket_path)

    relay_thread = threading.Thread(target=serve_connections, args=(listener, relay_handler, stop), daemon=True)
    relay_thread.start()

    child: subprocess.Popen[bytes] | None = None
    pending_signals: list[int] = []

    def forward(signum: int, _frame: FrameType | None) -> None:
        stop.set()
        pending_signals.append(signum)
        if child is not None:
            _forward_signal(child, signum)

    previous_handlers = _install_signal_handlers(forward)
    try:
        child = subprocess.Popen(
            list(command),
            env=_child_environment(listen_host, actual_port),
            start_new_session=os.name == "posix",
        )
        for signum in pending_signals:
            _forward_signal(child, signum)
        return_code = child.wait()
        return 128 - return_code if return_code < 0 else return_code
    finally:
        stop.set()
        listener.close()
        relay_thread.join(timeout=2)
        _restore_signal_handlers(previous_handlers)
        if child is not None:
            _stop_child(child)


def _port(value: str) -> int:
    try:
        port = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    serve_parser = subparsers.add_parser("serve", help="run the host Unix-socket CONNECT proxy")
    serve_parser.add_argument("--socket", required=True, type=Path, help="Unix socket to create")
    serve_parser.add_argument("--ready-file", required=True, type=Path, help="file created after the socket is listening")

    relay_parser = subparsers.add_parser("relay", help="relay loopback TCP to the host proxy and run a command")
    relay_parser.add_argument("--socket", required=True, type=Path, help="host proxy Unix socket")
    relay_parser.add_argument("--listen-host", default="127.0.0.1", choices=("127.0.0.1",))
    relay_parser.add_argument("--listen-port", default=3128, type=_port)
    relay_parser.add_argument("command", nargs=argparse.REMAINDER, help="command to run, conventionally after --")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.mode == "serve":
            return run_serve(arguments.socket, arguments.ready_file)

        command: list[str] = arguments.command
        if command[:1] == ["--"]:
            command = command[1:]
        if not command:
            parser.error("relay requires COMMAND after --")
        return run_relay(arguments.socket, arguments.listen_host, arguments.listen_port, command)
    except (OSError, ValueError) as exc:
        print(f"claude egress proxy: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
