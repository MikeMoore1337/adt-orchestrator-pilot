#!/usr/bin/env python3
"""No-model positive callback and negative egress probe for scoped IO570 proxy.

Native Codex sandbox only; never calls Codex exec or a model or GitHub API.
Uses a disposable linked Git worktree and a single local HTTP canary server.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
import os
import subprocess
import tempfile
import urllib.error
import urllib.request

from issue_orchestrator.domain.models import AgentConfig
from issue_orchestrator.domain.sandbox_scope import SandboxScopeContext, compute_session_scope
from issue_orchestrator.execution.agent_runner_providers.codex import CodexProvider
from issue_orchestrator.infra.hooks.codex_session import verify_codex_runtime_home

CODEX = Path.home() / ".local/share/adt-io570/codex-0.167.0/bin/codex"
PILOT_WORKTREES = Path.home() / "projects/adt-orchestrator-pilot-worktrees"
FLAG = "ISSUE_ORCHESTRATOR_IO570_LOOPBACK_PROXY"
CANARY = b"IO570_NO_MODEL_CALLBACK"


def git(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        check=True, timeout=20,
    )


def main() -> int:
    if os.environ.get(FLAG) != "1" or not CODEX.is_file():
        raise RuntimeError("IO570 proxy opt-in or pinned Codex binary missing")
    if not PILOT_WORKTREES.is_dir() or PILOT_WORKTREES.is_symlink():
        raise RuntimeError("Trusted pilot worktree parent missing or unsafe")
    if os.environ.get("OPENAI_API_KEY") or os.environ.get("CODEX_API_KEY"):
        raise RuntimeError("Paid API keys are forbidden")
    received = Event()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = min(64, int(self.headers.get("Content-Length", "0")))
            data = self.rfile.read(length)
            if self.path == "/io570-callback" and data == CANARY:
                received.set()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ACK")
            else:
                self.send_error(400)

        def log_message(self, *_args: object) -> None:
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/io570-callback"
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            if opener.open(urllib.request.Request(url, CANARY), timeout=3).read() != b"ACK":
                raise RuntimeError("Host loopback control failed")
            print("HOST_LOOPBACK_CONTROL=PASS")
            received.clear()

            with tempfile.TemporaryDirectory(
                prefix=".io570-proxy-", dir=PILOT_WORKTREES
            ) as tmp:
                base = Path(tmp) / "base"
                linked = Path(tmp) / "linked"
                git("init", "-q", "-b", "main", str(base))
                (base / "README.md").write_text("synthetic\n", encoding="utf-8")
                git("add", "README.md", cwd=base)
                git(
                    "-c", "user.name=IO570Probe",
                    "-c", "user.email=probe@example.invalid",
                    "commit", "-qm", "synthetic", cwd=base,
                )
                git(
                    "worktree", "add", "-q", "-b", "7-io570-probe/agent",
                    str(linked), "HEAD", cwd=base,
                )
                scope = compute_session_scope(
                    AgentConfig(
                        prompt_path=Path(".prompts/dev.md"),
                        prompt_relative=".prompts/dev.md",
                        provider="codex", sandbox=True,
                    ),
                    SandboxScopeContext(task_kind="code", worktree=linked),
                )
                if scope is None:
                    raise RuntimeError("Missing original sandbox scope")
                argv = CodexProvider().apply_scope(scope)
                if argv[:5] != ["--strict-config", "-a", "never", "-C", str(linked)]:
                    raise RuntimeError("Codex scope shape changed")
                if argv.count("features.network_proxy=true") != 1:
                    raise RuntimeError("Managed proxy feature not enabled")
                profiles = [
                    v for v in argv
                    if v.startswith("permissions.issue_orchestrator_scope=")
                ]
                if len(profiles) != 1 or (
                    'domains = { "127.0.0.1" = "allow" }' not in profiles[0]
                    or "allow_local_binding = false" not in profiles[0]
                    or "allow_upstream_proxy = false" not in profiles[0]
                    or "enable_socks5 = false" not in profiles[0]
                ):
                    raise RuntimeError("Unexpected proxy network policy")

                client = r'''
import os
import sys
import urllib.error
import urllib.request

mode, port = sys.argv[1:]
host = "127.0.0.1"
url = f"http://{host}:{port}/io570-callback"
if mode == "external":
    url = "https://example.com/"
elif mode == "other-host":
    url = f"http://localhost:{port}/io570-callback"
elif mode == "direct":
    # A direct loopback request is the *desired* callback, not an egress
    # bypass. Probe an EXTERNAL destination without using a proxy instead.
    url = "https://example.com/"

if mode == "direct":
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
else:
    os.environ["NO_PROXY"] = ""
    os.environ["no_proxy"] = ""
    opener = urllib.request.build_opener()

try:
    request = urllib.request.Request(url, b"IO570_NO_MODEL_CALLBACK")
    with opener.open(request, timeout=4) as response:
        result = response.read()
    if mode == "callback" and result == b"ACK":
        print("RESULT=CALLBACK_PASS")
    else:
        print("RESULT=UNEXPECTED_NETWORK_ACCESS")
        sys.exit(3)
except urllib.error.HTTPError as exc:
    # A reachable HTTP service/proxy is not proof of network isolation.
    print("RESULT=HTTP_RESPONSE:" + str(exc.code))
    sys.exit(4)
except (urllib.error.URLError, TimeoutError, OSError) as exc:
    if mode == "callback":
        print("RESULT=CALLBACK_FAIL:" + type(exc).__name__)
        sys.exit(2)
    print("RESULT=DENIED:" + type(exc).__name__)
    # Denial must be a nonzero exit. Zero previously caused false FAILs.
    sys.exit(2)
'''
                env = os.environ.copy()
                env["CODEX_HOME"] = str(verify_codex_runtime_home())
                values: dict[str, tuple[int, str]] = {}
                for mode in ("callback", "external", "other-host", "direct"):
                    received.clear()
                    result = subprocess.run(
                        [
                            str(CODEX), "sandbox", "--permission-profile",
                            "issue_orchestrator_scope", "-C", str(linked),
                            *argv[5:], "--", "/usr/bin/python3",
                            "-c", client, mode, str(server.server_port),
                        ],
                        cwd=linked, env=env, capture_output=True,
                        text=True, timeout=30, check=False,
                    )
                    result_text = result.stdout.strip()
                    values[mode] = (result.returncode, result_text)
                    if mode == "callback":
                        if (
                            result.returncode != 0
                            or "RESULT=CALLBACK_PASS" not in result_text
                            or not received.is_set()
                        ):
                            print("LOOPBACK_CALLBACK_GATE=FAIL")
                            return 1
                        print("LOOPBACK_CALLBACK_GATE=PASS")
                    else:
                        if (
                            result.returncode != 0
                            and result_text.startswith("RESULT=DENIED:")
                            and not received.is_set()
                        ):
                            print(mode.upper().replace("-", "_") + "_DENY=PASS")
                        else:
                            label = mode.upper().replace("-", "_")
                            print(label + "_DENY=FAIL")
                            print(label + "_OBSERVED_EXIT=" + str(result.returncode))
                            print(label + "_OBSERVED_RESULT=" + result_text[:220])
                            if result.stderr.strip():
                                print(label + "_SANDBOX_ERROR=" +
                                      " ".join(result.stderr.splitlines())[-250:])
                            return 1

                print("MODE=NO_MODEL_NO_GITHUB_API")
                print("OTHER_127_0_0_1_PORTS=NOT_RESTRICTED_BY_DOMAIN_POLICY")
                print("IO570_MANAGED_PROXY_GATE=PASS")
                return 0
        finally:
            server.shutdown()
            thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
