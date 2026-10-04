# The rule shipped, its enforcement was unreachable for four days — and 94 of the 95 rows in the guard's log are its own test suite

**Keywords:** regex tested in isolation not through the hook, unreachable guard pattern precondition, word boundary on regex stem, Stop hook exit code test, self-test rows in production audit log, enforcement did not ship with the rule, guard registered but never executing, differential test one word changed, instructions decay enforcement doesn't

**Incident date:** rule landed 2026-09-25, defects measured 2026-09-28, fixed 2026-09-29 · **Internal refs:** #2052, #2764, #3058 · **Status:** fixed (three defects repaired, hook-level tests added) ; one further defect found while writing this postmortem is **open** — the guard may never have run at all for its first 75 days

---

## What broke

A rule was added to this system's standing instructions on 2026-09-25 (commit `5ab63a31`): the external deep-research call is never skipped to save money. In the operator's words, which are quoted in the rule itself:

> "i know it costs money, do not save money on sonardeep at the cost of building a shitty system that costs me a lot more money and time"

The core thesis of this repository is that instructions decay and enforcement does not ([ADR-002](../adr/002-hooks-as-enforcement-not-instructions.md)), so the rule shipped with four new patterns in an existing `Stop` hook — the guard that refuses to let a turn end while it contains a cost-avoidance excuse. The patterns were checked **9 of 9 against the regexes in isolation** and declared working.

They were unreachable in production. The rule had no enforcement behind it for four days, while the log and the commit both said it did.

## How it was detected

Three days later, a session ran **the hook** — not the regexes — against the excuses it was supposed to block, and watched the exit code. Everything fell out of that one change of instrument.

## Root cause

Three defects, all invisible to a test that imports the pattern list and calls `re.search`:

**1. The new patterns were behind the wrong precondition.** The hook's `main()` first checks whether the turn mentions runtime or speed at all, and returns early if not — a sensible gate when every pattern was about runtime. The four research-cost patterns were added *inside* that gate, so they could only fire when the turn happened to also mention a runtime. Measured directly: **the identical excuse exits 0 without the word "minutes" in the turn and 2 with it.** The excuse is the same; the enforcement depends on an unrelated word appearing nearby. The repair gives research patterns their own precondition — the turn names the research tool — and makes the two gates independent.

**2. A pre-existing pattern could never match the phrase the rule names verbatim.** The stem list carried a trailing word boundary:

```python
r"\bnot\s+worth\s+(?:optimiz|the\s+effort|refactor|restructur)\b"   # before
r"\bnot\s+worth\s+(?:optimiz\w*|the\s+effort|refactor\w*|restructur\w*)\b"   # after
```

`optimiz\b` matches only the bare stem "optimiz", which is not a word. **"Not worth optimizing" — the exact phrase the standing instructions ban by name — could never match.** This one was not from the 2026-09-25 change; it had been shipped and passing its isolated regex checks since July.

**3. There was no test of the hook.** The "9 of 9" exercised the patterns in isolation and never ran the process, which is precisely why it could see neither defect 1 (the precondition lives in `main()`, not in the pattern) nor defect 2 (the isolated check was written with the stem, not with the real phrase).

The deeper cause is a single substitution: **a regex test is a test of a string, and the thing that decides whether a turn is blocked is an exit code.** Everything between the pattern and the exit code — preconditions, early returns, input parsing, registration — is untested by construction, and that is where all three defects lived.

## Blast radius

Four days (2026-09-25 to 2026-09-29) in which a standing instruction that exists to stop the agent from reasoning its way out of a $0.50–1 research call had no working enforcement, in a system whose own architecture decision says instructions alone do not hold. For defect 2, the window is **75 days** for the one phrase the rule quotes.

No instance of the excuse being accepted during that window has been recovered, because the guard logged nothing during it — which turns out to be its own finding.

## The fix

Commit `b3b5ad26`, 2026-09-29. Research patterns get an independent precondition; the stems are widened to `optimiz\w*`, `refactor\w*`, `restructur\w*`; and a test file drives **the real hook as a subprocess and asserts its exit code** over 14 cases, built as differential pairs where one word decides the outcome:

- the same excuse with and without a runtime mentioned — both must block
- four legitimate mentions of the research call that must **not** block, including one that declines the call for a non-cost reason and one that quotes the operator's own rule
- two speed regressions that must block, plus a real optimization report that must not
- a turn with neither context, which the hook must decline to judge

14 of 14 pass.

One procedural note, because it is part of the record: the commit was made **by the operator from his own shell**, under his 2026-09-28 decision that sessions do not self-commit enforcement changes but hand off a reviewed diff. The proximate reason is also an instance of a defect class documented here: the effect-class guard refuses the commit from inside a session, and its bypass reads an environment frozen at session start, which is the bypass-channel class documented in [PM-014](014-the-escape-hatches-that-never-existed.md).

## Has the guard fired since?

This is where the postmortem turned.

The guard's audit stream holds **95 rows in total**. Clustering them by time gaps shows six bursts:

| when | rows | span | what it is |
|---|---|---|---|
| 2026-09-28 19:17 | 10 | 42s | repair in progress |
| 2026-09-28 19:19 | 28 | 34s | repair in progress |
| 2026-09-28 21:18 | 28 | 44s | repair in progress |
| 2026-09-28 23:51 | 14 | 2.9s | the 14-case suite |
| 2026-09-29 16:18 | 14 | 1.0s | the 14-case suite |
| 2026-10-01 16:04 | 1 | — | **production block** |

**94 of the 95 rows are the test harness driving the hook. Exactly one is a real block** — a turn on 2026-10-01 that tried to skip the research call, refused on the `research-skipped` pattern. So the repair works, and the enforcement is real; but the log that would be used to *measure* this guard under [ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md) overstates its production activity by **95×**, because the hook writes an identical audit row whether it was invoked by a turn ending or by `pytest`. A sibling `Stop` guard in the same repository does stamp its self-tests (`reason:selftest`, 20 rows in the same week). This one does not.

That contamination class was documented here 23 days earlier — [PM-055](055-the-audit-log-could-not-be-counted.md) names "self-test contamination in production logs" among the three errors that made a guard look quieter than it was. Documenting a measurement hazard did not prevent the next guard from shipping with it. A marker field is one line; it is not in anyone's definition of done.

**And the earliest of those 95 rows is dated 2026-09-28 — 75 days after the hook was committed.** The hook and its `Stop` registration landed in the same commit on 2026-07-14, the registration string was added once and never removed, and the pre-image already logged `{"decision": "skip", "reason": "no speed context in response"}` on the no-context path, which should fire on very nearly every turn. Three sibling speed hooks from the same era logged continuously from 2026-07-15 (23,347 / 242 / 209 rows), so the audit file itself was live the whole time. The 2026-09-29 repair changed neither the audit path, nor the hook name, nor the `_audit()` function, nor the input parsing.

A wired `Stop` hook that logs on every turn cannot produce zero rows in 75 days unless **it was not executing**. That is filed open as **#3058** and deliberately not concluded here: the cheap next step is to drive the registered command exactly as the settings file spells it and watch for a row. If it confirms, then "the patterns were unreachable for four days" understates the finding — the guard's first real execution was the day someone finally ran it by hand.

## Lessons for agent-driven development

1. **Test the unit that makes the decision.** For a hook, that is the process and its exit code — not the regex, not the matcher function. Everything between the pattern and the exit code is where the defects were: a precondition, a word boundary, and possibly the registration itself.
2. **"9 of 9 patterns verified" is a sentence about strings.** When a count of passing checks is offered as evidence that enforcement works, ask what instrument produced it. Ours had never started the process it was describing.
3. **Write differential pairs.** "Same excuse, one word changed, opposite expected outcome" is what exposed the precondition coupling. A suite of positives would have passed on a guard that only fires when an unrelated word is present.
4. **A rule and its enforcement must land in the same change, and the enforcement needs a test before the rule is called shipped.** Four days of a documented, quoted, believed-in rule with nothing behind it is the exact decay this system's architecture exists to prevent.
5. **Stamp self-test invocations in the audit row.** One field. Without it, every later measurement of the guard — fire rate, bypass rate, promotion decisions — is computed from a log in which the tests outnumber production 94 to 1.
6. **An empty fire log is a finding, not a quiet guard.** The absence of rows was sitting in plain sight for 75 days and read as "it never needed to fire." A guard with a no-op logging path should produce rows on nearly every turn; if it does not, it is not running.
