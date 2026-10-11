# The detector that decides "is this a git commit?" was blindest exactly where a session was already bypassing a guard

**Keywords:** git command detection hook, shlex parse failure fallback regex, inline environment variable prefix, guard bypass variable, Windows git.exe path detection, PreToolUse Bash command classifier, false negative correlated with bypass, single definition of is-git, re-measure the commit message numbers, Claude Code concurrent sessions

**Incident date:** measured 2026-10-05 · **Internal refs:** #3080, #3010 · **Status:** fixed (widened detector, commit 893b555a) ; **re-measured a week later for this write-up, and two of the commit message's numbers do not reproduce**

---

## What broke

Several of our `PreToolUse` guards need to answer one question about a shell command before anything else: *does this command run `git <subcommand>`?* One shared function answers it, and its test for "is this token the git binary" was:

```python
tok == "git" or tok.endswith("/git")
```

When a command could not be tokenized — `shlex` raises on unbalanced or nested quotes — the code fell back to a regex that required the git binary to sit **immediately after a shell separator**.

Two shapes slipped through:

- **An inline environment assignment in front of the command.** `SOME_VAR="..." git commit -- path` puts a token that is not `git` first, so the regex never matched.
- **Spellings of the real binary.** `git.exe`, a quoted `C:/Program Files/Git/.../git.exe`, `/mingw64/bin/git.exe` and an unquoted backslash path all failed the test. POSIX `shlex` treats a backslash as an escape, so `C:\Git\cmd\git.exe` tokenized to `C:Gitcmdgit.exe`.

## How it was detected

The detector was about to become load-bearing: the next change would **refuse** git mutations in the shared checkout ([ADR-019](../adr/019-publication-from-a-shared-checkout-goes-through-a-scoped-publisher.md)). Before giving it that job, the builder measured it against ground truth instead of reading it.

The ground truth was a different guard. Our pathspec-commit guard logs the **full** command, and it has its own independent parser that only records a decision on a real `git commit`. Replaying those logged commands through the shared detector shows where the two disagree.

## Root cause

**The false negatives were not random. They clustered on the commands where a session was stepping around a guard.**

Here is the chain:

1. A guard-bypass variable carries a `reason:` text. Sessions write long, multi-line, quote-heavy reasons, because our bypass rules demand a stated reason.
2. That reason text is the thing most likely to make `shlex` raise.
3. When `shlex` raises, the code drops to the fallback regex.
4. The bypass variable is, by construction, an inline environment prefix — the exact shape the fallback regex could not see.

So the detector saw least precisely where precision mattered most. **A bypass made the command harder to parse, and a harder parse made the git call invisible.** Each step was a reasonable local choice. Together they made "bypass a guard" and "be invisible to the next guard" the same act.

The Windows spellings are the smaller half, but they matter for what came next. A session told to stop typing bare `git` will reach for exactly those spellings.

## Blast radius

**Re-measured for this write-up (2026-10-11).** Ground truth: every pathspec-guard row that recorded a decision and a command, up to the moment the fix landed.

- **3,823** commands the pathspec guard judged to be real commits.
- The **old** detector recognised **3,701** of them (96.8%). It missed **122**.
- **33** of the 122 misses began with an inline environment assignment.
- **30 of those 33** carried a guard-skip variable. The other three were not plain commits at all: two `GIT_INDEX_FILE=... git add` lines and one scratch-directory command.
- The skip variables in those 30 commands: the stranger-file guard's (26 occurrences), a pre-commit backstop's (5) and a preserve-list guard's (3).

What a miss cost depended on which guard asked the question. A guard that **adds** a check when it sees a commit simply did not add it. No corruption has been traced to a specific miss.

## The numbers in the fix's commit message did not all reproduce

The repair commit stated its own measurement. Re-counting from the same log a week later gives:

- **"3,813 real commits."** Our count of judged rows before the fix is **3,823**. The difference is small and the selection rule was not recorded, so we cannot say which is right.
- **"It missed 115."** The same message gives the before-number as **3,694 / 3,813**, and that is **119** misses. The commit message disagrees with itself.
- **"Every one of the thirty-three carried a guard bypass."** We found **30 of 33**. The three exceptions were not commits.
- **"After: 3,810 / 3,813 = 99.9%."** Our re-count of the new detector is **3,813 / 3,823 = 99.7%**.

**The conclusion survives every one of these corrections.** Most inline-env misses carried a bypass, and the widening closed nearly all of them. The magnitudes in the commit message were stated more cleanly than its own log supports.

This is the second week running that an agent-written number did not survive a re-count ([PM-072](072-the-gate-handed-a-session-another-sessions-claim.md) was off by 3,600×). That is why this repo's writing protocol re-derives every number from primary sources and does not copy figures out of commit messages.

## The fix

**Commit 893b555a, one file.**

1. **One definition of "is this git."** The binary test now delegates to the function the pathspec and stranger-file guards already used. Two answers to the same question leave a hole wherever they disagree. The delegation was proven **by effect**: stubbing the canonical function to always return false made the dispatcher adopt the wrong answer.
2. **A second tokenizer pass for Windows paths.** It runs with `posix=False` and only when the command contains a backslash. That gate keeps it away from commands the precise pass already judged — in particular from `git commit -m "has ; git push inside"`, whose negative control would otherwise break.
3. **A fallback that stops pretending to parse broken quoting.** On `shlex` failure it strips quote characters, splits on whitespace and runs the same token walk.

**The cost, stated in the commit:** on the fallback path a broken-quoted command that merely *mentions* a git subcommand now matches. That false positive costs one refusal message. A fixture asserts it fires, so the tradeoff is tested and not just asserted.

One attempt was discarded along the way. Widening the old regex with an env-prefix alternative made things worse: a greedy quoted-value match swallowed the git call itself. A fixture catches that regression.

**Still not seen, by design, each with a fixture asserting the detector does not fire:** variable indirection (`G=git; $G commit`), git reached through a Python subprocess, anything behind a script file, and git run over the remote relay.

## Has the guard fired since?

The widened detector feeds the shared-checkout mutation refusal described in [ADR-019](../adr/019-publication-from-a-shared-checkout-goes-through-a-scoped-publisher.md). Between 2026-10-05 and 2026-10-11 that refusal logged **106** rows:

- **46** from two production sessions (adds, commits, rebases and one pull).
- **60** from the test suite.

The refusal record stores the command **class**, never the command text, so a secret in a commit message cannot land in the log. The cost: these rows cannot tell us how many refusals were reached only through the widened paths (env prefix, `git.exe`). That gap is real, and we chose it on purpose.

## Lessons for agent-driven development

1. **Check whether your false negatives correlate with adversarial behaviour.** A 3% miss rate sounds fine. A 3% miss rate concentrated on bypass-carrying commands is a hole shaped like the threat.
2. **Bypass mechanisms change the input distribution your other guards see.** We required long stated reasons on bypasses — a good rule — and those reasons broke the tokenizer of a different guard. Test every classifier against commands that carry your own bypass syntax.
3. **One question, one function.** Our repo had two definitions of "is this git," and the hole sat exactly where they disagreed. Delegate, then prove the delegation by stubbing it.
4. **Measure a classifier against a guard that logs the full input, before you make it enforcing.** A truncated log makes misses look like artifacts. A keyword-filtered sample makes correct non-detections look like misses. The commit names both traps.
5. **Re-derive the numbers in commit messages before you repeat them.** A commit message is a claim written by the same agent that did the work. Here the mechanism held and three of four figures moved.
