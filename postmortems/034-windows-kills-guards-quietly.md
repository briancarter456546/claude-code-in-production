# Three Ways Windows Quietly Killed Our Cross-Platform Automation

**Keywords:** Windows Git Bash hooks, exec bit lost, file mode 100644, persisted cd hooks, Windows file locking, WinError 32, cross platform CI, line endings exec permissions

**Incident window:** 2026-05→07 (three mechanisms) · **Internal refs:** tasks #799/#800, #981; the 53-hour handle incident · **Status:** all three fixed/contained; platform checks joined the self-test suite

---

## What broke

The stack spans a Windows dev PC, a Linux droplet, and a macOS worker. Three separate incidents traced to the same tectonic seam — POSIX assumptions meeting Windows reality:

1. **The exec bit that never traveled (#799/#800):** shell scripts authored on Windows commit with mode `100644` — no execute permission, because NTFS has no exec bit for git to preserve. On the droplet, the git-sync pulled the scripts and then couldn't execute them. Result: a **four-day silent outage of the sync-deployed automation** — the scripts were present, current, readable, and dead. Nothing errored loudly; the invoking layer treated permission-denied as skip.
2. **The `cd` that outlived its command (#981):** the Bash tool's working directory *persists between calls*. A session legitimately `cd`-ed into a subdirectory; five hooks that resolved helper paths relative to cwd began failing — **silently**, exit-code-swallowed — for days. (The loud version of this same class blocked every tool call one day in June — see [PM-019](019-when-the-safety-layer-became-the-outage.md).)
3. **The 53-hour file handle:** a crashed session's process held a Windows exclusive handle on an output file. Days later, `git pull --rebase` failed with `WinError 32` (file in use by another process) — version control blocked by a process that no longer had a purpose, only a handle. Windows file locking is mandatory, not advisory; a dead session's grip outlives its mind.

## How it was detected

1: the four-day gap — noticed when expected automation effects didn't materialize, traced to `permission denied` in a log nobody watched. 2: hooks that "should have" fired, not firing; found during the relative-path audit. 3: loudly, at the rebase — the diagnosis (which process, why, since when) took the forensics; the handle's age (53+ hours) came from process start times.

## Root cause

One deep cause in three costumes: **the toolchain's contract silently narrows on Windows** — exec bits don't exist (so git can't carry them), cwd is session-state (so relative paths are time bombs), and file locks are mandatory (so crashed processes leave physical debris). Code written against POSIX intuitions doesn't fail on Windows; it *mostly works*, which is the most expensive amount of working.

## Blast radius

Four days of dead sync-deployed automation; days of five silently-dead hooks; one blocked repository until the handle was hunted. Plus the standing tax: every future script authored on the PC carries the exec-bit risk until the check below catches it.

## The fix

- **Exec bits enforced at commit:** a pre-commit check asserts `100755` on `*.sh` (git tracks the mode even if NTFS won't); the fix for existing files was `git update-index --chmod=+x`, applied fleet-wide. The invoking layer's permission-denied path was also promoted from skip to ERROR (see [PM-033](033-production-degraded-politely.md)'s severity law).
- **Absolute paths, hook-anchored** ([PM-019](019-when-the-safety-layer-became-the-outage.md)'s contract): hooks resolve from their own file location, never cwd; the dispatcher self-test asserts it.
- **Handle hygiene:** crashed-session cleanup includes handle enumeration on repo paths; the rebase-blocked runbook names the tools (`handle`/Resource Monitor) so the next occurrence is minutes, not an afternoon.

## Has the guard fired since?

The exec-bit pre-commit check has caught fresh `100644` shell scripts repeatedly — Windows authorship keeps producing them; the check keeps them from traveling. The cwd class is covered by the dispatcher's self-test. No repeat of the multi-day silent variants.

## Lessons for agent-driven development

1. **Cross-platform failures are mostly *silent narrowings*, not crashes.** Exec bits, locks, and cwd semantics don't error on the authoring machine — they detonate on the consuming one. Test where it runs.
2. **git carries file modes; filesystems don't have to.** On Windows, the mode in the index is a *decision*, not an observation — enforce it explicitly.
3. **Anything a session can change (cwd, env) is not a stable base for infrastructure.** Hooks and tools anchor to their own locations or inherit every session's wanderings.
4. **Crashed processes are physical objects on Windows.** Their handles block real operations days later; session-death cleanup must include the OS-level debris, not just the state files.
