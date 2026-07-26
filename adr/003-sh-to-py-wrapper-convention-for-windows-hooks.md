# ADR-003: Hooks are thin .sh shims that exec matching .py implementations

**Status:** Active · **Date:** 2026-03 (reconstructed) · **Internal refs:** hook wrapper convention, repo-wide

## Context

Claude Code executes hooks through a POSIX-ish shell even on Windows (Git Bash). The primary dev machine is a Windows PC; the droplet is Linux; the compute worker is a Mac. Early hooks written directly in bash accumulated Windows-specific landmines: path separator confusion, quoting differences, and the encoding trap — Windows defaults to cp1252, so any hook that read or wrote UTF-8 content through naive shell redirection could silently mangle it. Meanwhile all the real logic (parsing transcripts, querying state files, matching patterns) is far more testable in Python.

## Decision

Every hook is a **pair**: a `.sh` shim whose only job is to locate and `exec` the Python interpreter on a `.py` file of the same name, and the `.py` file where all logic lives. Conventions inside the Python side:

- UTF-8 explicitly declared on every file read/write (never rely on platform default).
- ASCII-only output (`[OK]`, `[FAIL]`, `-->`) — no unicode symbols that a Windows console codepage can garble.
- Exit-code contract kept in the Python layer so the shim never needs logic.

The shim is boilerplate by design; if a shim contains an `if`, it's wrong.

## Alternatives considered

- **Pure bash hooks.** Rejected after repeated Windows quoting/encoding bugs; also unloved to test.
- **PowerShell hooks.** Native on the PC but not portable to the Linux droplet or the Mac, and the harness invokes hooks through a POSIX shell anyway.
- **Single cross-platform binary.** Overkill; Python is already the project's lingua franca and is present on all three machines.

## Consequences

- Two files per hook — the hooks directory holds ~211 files for ~100 logical hooks. Noise, but greppable noise.
- Shim drift is possible (a `.sh` pointing at a renamed `.py`); caught by a self-test that walks pairs.
- All hook logic is unit-testable Python, which is what made per-hook self-tests (ADR-002's regret) feasible at all.

## What we'd do differently

Nothing major — this one paid for itself quickly. The only refinement: generate the shims from a template instead of copy-pasting them, which would have prevented the handful of drifted shims we've had to fix.
