# Codex Linux exact-file root patch for original Issue-Orchestrator #570

**This is not a new scheduler, a replacement engine, or an installed executable.** It is an optional, source-reviewed patch against official OpenAI Codex CLI v0.167.0, required only because the Linux bubblewrap backend attempts to mount `.git/.aws` descendants under *regular files* that are exact writable roots.

## Provenance

- Official upstream: https://github.com/openai/codex
- Official signed release tag: `rust-v0.167.0`
- Immutable release Git commit: `086ccc833bc9cf01024ad2dd6af7dbd421b6bf9a`
- Affected original Git blobs: `bwrap.rs=11959d0c02248f090a568efd5b53ee1fa0e6ad9c`, `bwrap_tests.rs=9f53e2c9e72406e59605bf1a6f7560040b33dfbc`
- Upstream reports: https://github.com/openai/codex/issues/40433 and https://github.com/openai/codex/issues/52651
- Does not change the original Issue-Orchestrator source pin `d4a79824ccd806089cf3f70ec632d39b8ee255ea`.

## Security property

For any writable regular file (including Git ref/reflog) Codex still binds **that file only** with write permission, and must not attempt to build protected `.git`, `.aws`, `.codex` or `.agents` directories *under the file*. For writable directories, generated metadata masks are unchanged. This prevents a deterministic filesystem bootstrap panic **without broadening permission over the file's parent directory**.

The patch adds a Rust regression test checking that the exact file write bind still exists, that synthetic child mount targets do not exist, and that directory metadata protections remain intact.

## To apply to a disposable, exact-version source checkout

```bash
git clone --filter=blob:none --depth 1 --branch rust-v0.167.0 https://github.com/openai/codex.git "$HOME/projects/codex-io570-src"
git -C "$HOME/projects/codex-io570-src" rev-parse HEAD
# Must equal 086ccc833bc9cf01024ad2dd6af7dbd421b6bf9a
python3 scripts/apply_codex_regular_file_fix.py "$HOME/projects/codex-io570-src"
python3 scripts/apply_codex_regular_file_fix.py "$HOME/projects/codex-io570-src" --apply
```

Source-only application does **not** make any existing Codex process safe. Building an official-source patched CLI and validating it requires a Rust 1.95.0 toolchain and original Codex dependencies. Do not replace the owner's original `~/.codex` release. Install any tested patched binary only as a separate isolated copy, with an independently verified checksum and a verified ChatGPT login.

Before any real model task, re-run `scripts/probe_linked_codex_sandbox.py` **in WSL2** against the isolated patched binary. Require `SHELL_BOOT=PASS`, `GIT_COMMIT=PASS`, `GH_CANARY_DENY=PASS`, `OUTSIDE_WRITE_DENY=PASS` and `LINKED_SANDBOX_GATE=PASS`. If Git commit fails because a missing `.lock` file cannot be created under a read-only parent, that is an additional security/compatibility blocker. Do **not** widen base `.git/refs`, disable the sandbox, reset the blocked Issue #7 or invoke the model.

## Install a verified CI-built copy (not yet released into main)

After the dedicated GitHub Actions build has completed SUCCESS **and produced an artifact**:

```bash
gh run download <EXACT_SUCCESSFUL_BUILD_RUN_ID> --repo MikeMoore1337/adt-orchestrator-pilot --name codex-io570-patched-linux-x86_64 --dir "$HOME/.local/state/adt-io570/build-artifact"
python3 scripts/install_patched_codex.py "$HOME/.local/state/adt-io570/build-artifact"
export PATH="$HOME/.local/share/adt-io570/codex-0.167.0-io570-patched/bin:$PATH"
unset CODEX_HOME
python3 scripts/probe_linked_codex_sandbox.py
```

The installer checks the exact Rust source commit, build-provenance marker and SHA-256 of the downloaded executable, refuses overwrite, keeps a separate original release intact and does not read credentials. Download the artifact from the **verified run** only. `scripts/start_guarded_pilot.sh` now refuses unpatched executables even if their version matches.

**Status: source patch prepared; native linked worktree execution NOT VERIFIED.**
