#!/usr/bin/env python3
"""No-model probe of a *running* original Control API with an invalid capability.

This diagnostic never submits a valid completion or accesses other repositories.
It returns PASS only when agent-callback authentication reaches the intake and
the intentionally bogus per-run capability is rejected (no ledger mutation).
Run outside the Codex agent sandbox in the operator's trusted WSL2 shell.
Never print or transmit any bearer token except to the verified 127.0.0.1 API.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import urllib.error
import urllib.request

from issue_orchestrator.infra.api_token import (
    read_existing_agent_callback_token,
)
from issue_orchestrator.infra.repo_lock import read_lock, is_locked


def main() -> int:
    repo = Path.home() / "projects/adt-orchestrator-pilot"
    if Path.cwd().resolve() != repo.resolve() or not (repo / ".git").is_dir():
        print("CONTROL_API_DIAGNOSTIC=WRONG_REPO")
        return 2

    lock = read_lock(repo)
    if lock is None or not is_locked(repo):
        print("CONTROL_API_DIAGNOSTIC=NOT_RUNNING")
        return 2
    if type(lock.http_port) is not int or not 1024 <= lock.http_port <= 65535:
        print("CONTROL_API_DIAGNOSTIC=NO_PUBLISHED_PORT")
        return 2

    try:
        cmdline = (Path("/proc") / str(lock.pid) / "cmdline").read_bytes()
    except OSError:
        print("CONTROL_API_DIAGNOSTIC=ENGINE_PROCESS_NOT_FOUND")
        return 2
    if b"issue-orchestrator" not in cmdline:
        print("CONTROL_API_DIAGNOSTIC=ENGINE_IDENTITY_MISMATCH")
        return 2

    callback_token = read_existing_agent_callback_token()
    if not callback_token:
        print("CONTROL_API_DIAGNOSTIC=AGENT_TOKEN_UNAVAILABLE")
        return 2

    raw = b'{"io570_no_model_probe":true}'
    digest = sha256(raw).hexdigest()
    data = json.dumps({
        "raw_bytes": base64.b64encode(raw).decode("ascii"),
        "content_sha256": digest,
        "submission_key": digest,
    }).encode("ascii")
    request = urllib.request.Request(
        f"http://127.0.0.1:{lock.http_port}/api/completion/submissions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {callback_token}",
            "X-Completion-Capability": "io570-invalid-" + secrets.token_hex(32),
        },
        method="POST",
    )
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect()
    )
    try:
        with opener.open(request, timeout=4) as response:
            # A bogus capability must NEVER be accepted.
            status = response.status
        print("CONTROL_API_DIAGNOSTIC=UNEXPECTED_ACCEPTANCE")
        print("CONTROL_API_HTTP_STATUS=" + str(status))
        return 1
    except urllib.error.HTTPError as exc:
        body = exc.read(4096)
        if exc.code == 401 and b"Invalid run capability" in body:
            print("CONTROL_API_AGENT_AUTH=PASS")
            print("CONTROL_API_INVALID_CAPABILITY_DENY=PASS")
            print("CONTROL_API_DIAGNOSTIC=PASS")
            return 0
        # Never print server bodies or headers: they may include secrets.
        print("CONTROL_API_HTTP_STATUS=" + str(exc.code))
        print("CONTROL_API_DIAGNOSTIC=REJECTED_BEFORE_CAPABILITY_OR_SERVICE_UNAVAILABLE")
        return 1
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print("CONTROL_API_TRANSPORT_ERROR=" + type(exc).__name__)
        print("CONTROL_API_DIAGNOSTIC=UNREACHABLE")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
