# Our pre-commit secret scanner reported clean on a diff it never read — and the trigger was one curly quote

**Keywords:** pre-commit hook secret scanning, subprocess text mode no encoding, UnicodeDecodeError reader thread, cp1252 undefined bytes Windows, empty stdout mistaken for empty input, fail-open security control, git diff --cached encoding, exit code 0 silent pass, unscanned diff is not a clean diff, errors=replace completeness

**Incident date:** 2026-10-03 · **Internal refs:** #3034, #3035 · **Status:** fixed (scanner v1.0 → v1.1, three fail-open layers removed) ; the new refusal branch fired in production the day it shipped — see below

---

## What broke

A git **pre-commit** hook scans the staged diff for literal API keys, tokens and session cookies and aborts the commit if it finds one. It lives at the commit layer rather than the editor layer for a reason documented in its own header: the original key leak in this system arrived through a path no `PreToolUse` hook can observe — the agent harness auto-added an allowlist entry to a settings file when a human approved a shell command with a literal value inline, and a harness mutation is not a `Write` tool call ([PM-030](030-the-secret-the-hooks-could-not-see.md)). The durable leak surface is `git commit`, so that is where the gate went.

The scanner read the diff like this:

```python
subprocess.run(["git", "diff", "--cached", "--unified=0", "--no-color"],
               capture_output=True, text=True)   # no encoding=
```

`text=True` with no `encoding` decodes the child's stdout using the platform default. On Windows that is **cp1252**. A byte cp1252 cannot decode raises `UnicodeDecodeError` — and it raises **on the thread `subprocess` uses to drain the pipe**, not on the calling thread. The function's own `try/except` therefore never sees it, `result.stdout` comes back empty, the caller reads "there is no staged diff", and the scanner reports **clean**.

Measured 2026-10-03: the hook **exits 0 after returning zero characters of diff, against a real staged diff of over 578,000 bytes.**

This is the failure mode that is worse than a crash. A crash in a pre-commit hook is fail-closed — any non-zero exit blocks the commit. This looked like success. The control ran, finished, and said clean.

## How it was detected

Not by a test, and not by the scanner. A session was committing an external reviewer's reply that contained **curly quotes**, noticed the scanner's silence did not match the size of what it was committing, and ran the same `git diff --cached` call by hand.

## Root cause

Two mechanisms stacked, and the second is the one that made the first invisible.

**1. The decode failure happened where nobody was catching.** Exceptions raised inside `subprocess`'s pipe-reader thread do not propagate to the caller. The caller sees a successful `run()` and an empty `stdout`.

**2. The function's return type could not express what had happened.** `scan_staged_diff()` returned a bare list of findings. An empty list meant both *"no secrets in the staged diff"* and *"no diff was read."* For a security control those are opposite conclusions, and conflating them in the type is the whole defect — the bug could not have been caught by reading the call site, because the call site was handling every value the signature allowed.

**The trigger was far narrower than "non-ASCII", and the narrowness is the interesting part.** Measured during the repair: cp1252 leaves **exactly five byte values undefined** (`0x81`, `0x8D`, `0x8F`, `0x90`, `0x9D`). Every other byte decodes to mojibake *without raising*. Of the typography this repository actually produces, only **U+201D — the closing curly double quote** — encodes to one of those five. So the scanner was not silently passing on "unicode." It was silently passing on effectively **one character**, which is why it survived months of commits: common em-dashes and opening quotes decoded to garbage and the scan proceeded on garbage, while one specific quote mark switched the control off entirely.

## Blast radius

Every commit whose staged content contained that one character received **no secret scanning at all**, and reported clean. This repository's review artifacts, reviewer replies and commit bodies routinely contain curly quotes, so the affected population is not small — and it is not enumerable after the fact, because a pass leaves no row that distinguishes "scanned and clean" from "never read."

No leaked credential has been traced to this window. That is a statement about what we can see, not an all-clear: the control that would have seen it is the one that was off.

A follow-on audit (#3035) found the same omission is **systemic, not local: 59 text-mode subprocess reads with no explicit encoding across 28 hook files, 58 of them capturing output.** Filed, not patched.

## The fix

Scanner v1.0 → v1.1, commit `45c4102b`. The operator's design rule for the patch, verbatim:

> "decode failure or reader failure != no secret found
>  decode failure or reader failure => refuse / scanner unavailable"

Implemented as:

- **Bytes mode** (`text=False`), no implicit decoding anywhere.
- **git's exit status is checked**, because a failed git is not an empty diff.
- The decode is **explicit and strict first**. On invalid UTF-8 the text is recovered with `errors="replace"` *and an error is recorded* — because replacement keeps the scan running but does not establish that it was **complete**. A replacement character could be sitting where a secret's bytes were.
- `scan_staged_diff()` now returns **`(findings, error)`**. The signature change is the repair; the rest is detail.
- **Three fail-open layers removed, not one:** the reader's blanket return of an empty string, a `return 0  # fail-graceful: never block on internal error` inside `main()`, and a module-level `except Exception: sys.exit(0)`. All three now refuse.
- The refusal **distinguishes the two states in both the message and the audit row**: `precommit_secret_scanner_block` (a secret was found) versus `precommit_secret_scanner_unavailable` (nobody can tell whether there is a secret). The operator of a blocked commit needs to know which one happened.
- The bypass is preserved and still audited.

**12 tests**, each driving the real hook file as a subprocess in a real repository with real staged content — including `malformed_bytes_with_a_secret_are_never_reported_clean`, `git_exiting_non_zero_is_not_read_as_an_empty_diff`, and `an_unavailable_scan_is_audited_as_unavailable_not_as_clean`.

The repair was then **verified against v1.0 by reverting the reader and both handlers in the production file**: 8 repair-specific tests failed, 4 unchanged-behaviour proofs passed, and the file was restored byte-identically. That check caught two of the repairing session's own errors:

1. One test was in the wrong partition. Its "clean scan is silent on stderr" assertion is *itself* evidence of the repair, because v1.0 printed a reader-thread traceback at that point — so it became its own test rather than a control.
2. **The restore was not byte-exact.** It read the file as text and wrote it back with `newline=""`, rewriting CRLF to LF, and failed its own hash verification — leaving a security guard in an unverified state until the content was checked by hand. The restore now reads and writes **bytes**. A verification procedure that mutates the artifact it is verifying is a second instance of this postmortem's own class.

## Has the guard fired since?

Yes, on the day it shipped, and it fired on the branch that did not previously exist. One audit row, 2026-10-03:

```
precommit_secret_scanner_unavailable  {"reason": "undecodable_bytes:offset=9626357"}
```

A commit was refused because 9.6 MB into the staged diff sat a byte the scanner could not read, so it declined to call the diff clean. Under v1.0 that commit would have passed with an empty read and a clean verdict.

Zero `_block` rows so far — no literal secret has been staged since the repair. The refusal path is proven in production; the detection path is proven only by the test suite.

## Lessons for agent-driven development

1. **An empty read and an empty input must not share a return value.** This is a type problem before it is a security problem. If a function can answer "nothing found," it must be unable to say that when it found nothing *because it looked at nothing* — separate the channel, as `(findings, error)` does.
2. **Exceptions inside a subprocess reader thread are invisible to your `try/except`.** Any `subprocess.run(..., text=True)` without an explicit `encoding` is a latent silent-empty-output bug on Windows. We had 59 more of them.
3. **"Fail-graceful" is the wrong default for a control, and it is usually written as a comment explaining itself.** Three separate handlers in one 300-line file each chose to exit 0 on failure, each with a reasonable-sounding comment. For enforcement code, grep your own codebase for `fail-graceful`, `never block on`, and bare `except Exception: return 0`.
4. **Audit the state, not just the outcome.** `allow` and `could-not-tell` were the same row before this repair. A log that cannot distinguish them cannot be used to measure the control later ([ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md)).
5. **Verify a repair by breaking it again in the production file — and restore in bytes.** Reverting the fix and watching the new tests fail is the only evidence that the tests test the repair. The restore step is itself a destructive operation on a security guard, and ours silently rewrote every line ending the first time.
6. **A regression test that asserts exit 0 would have hidden this.** The defect *was* exit 0. The test has to assert the refusal, on content built to trigger the specific failure — one curly quote, not "some unicode."
