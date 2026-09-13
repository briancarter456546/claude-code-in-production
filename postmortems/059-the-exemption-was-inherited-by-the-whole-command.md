# A Claude Code safety hook exempted any Bash command containing a git commit — so "commit; place an order" skipped the guard entirely

**Keywords:** PreToolUse hook bypass, compound shell command, command contains substring exemption, && ; chaining bypass guard, shell command parsing in hooks, allowlist inheritance, brokerage read-only guard, false positive prose blocking, corpus replay test, heredoc body scanning

**Incident date:** 2026-09-08 · **Internal refs:** #2687, #2681 · **Status:** fixed the same day; five smuggling shapes pinned as must-block tests

---

## What broke

A PreToolUse hook keeps agent sessions **read-only against a brokerage API**: any Bash command that looks like it could place, modify, or cancel an order is blocked. Like most content guards it had exemptions, and one was sensible on its face — commit messages routinely *describe* trading changes, so a command that was a git commit skipped the scan.

The test for "is a git commit" was **"the command string contains a git commit."** A compound command whose first clause was a commit and whose second clause invoked an order-placing script — joined with `;` or `&&` — contained a commit. The whole string was exempt. The guard never looked at the second clause.

Verified before the fix by calling the detector directly: it returned "exempt" for a commit, a semicolon, and an order-placing interpreter invocation.

## How it was detected

Not by an attack, and not by the guard. It surfaced while a different session was fixing the **opposite** failure in the same hook: the guard was hard-blocking ordinary marketing notes, and had even blocked the session's own bug report about the false positive. Reading the exemption logic to understand why prose was blocked exposed why a real order would not have been.

That false positive, traced properly: not the business term the report named, but a bare English verb in the trigger list ("liquidates") appearing twice in the notes file — two matches, the two blocks reported.

## Root cause

**An exemption inherits whatever else is in its unit of evaluation.** A guard that evaluates the whole command string and exempts on a substring grants that exemption to every clause concatenated alongside it. Shells make concatenation free: `;`, `&&`, `||`, pipes, command substitution, heredocs.

The same detector was used in two other places *inclusively* — to **add** checks when a commit was present — and there "contains" is safe: extra scrutiny cannot be smuggled. The bug is specific to using a containment test to **skip** scrutiny. Nothing in the code distinguished those two uses; they called the same function.

This is the sibling of [PM-017](017-the-guard-that-suppressed-itself.md). There, an exemption pattern matched the violation itself. Here, it matched something *next to* the violation.

## Blast radius

**No order was placed and no bypass was observed in use.** The replay of 4,818 recorded commands after the fix produced zero new blocks, so no command in that log used the hole. The exposure was a latent hole in a control whose entire job is to be unconditional.

The false-positive side had real cost: a guard that blocks prose, including reports about itself, is the kind that trains sessions to route around it ([PM-021](021-alarm-fatigue-by-the-numbers.md)).

## The fix

- **Exemptions now require a solitary invocation.** A new check establishes the command is *only* a git commit — no separators, pipes, substitution, or redirection. The two inclusive call sites keep the looser detector, deliberately.
- **Trigger words were tiered.** API identifiers block unconditionally, coverage unchanged. The two bare English verbs block only when a brokerage identifier is also present — and the context set is identifiers *only*, because gating English words on other English words ("position", "portfolio") reproduces the defect: the file that was wrongly blocked contained both.
- **Prose heredoc bodies are skipped only when redirected to a file with a known prose extension.** The first draft skipped any heredoc body; replaying recorded commands caught it skipping the body of a heredoc fed straight to an interpreter — which is code, not prose. The rule became an allowlist.
- **Filing a bug about the guard can no longer be blocked by the guard:** one invocation of the reporting CLI with literal arguments is exempt — under the same solitary-invocation rule.

## Has the guard fired since?

Verification at the fix, from the commit record:

- **35 test cases green**, including the real incident file replayed as a heredoc and **five smuggling shapes that must still block**.
- A mutation test: every unconditional trigger alternative is load-bearing.
- **Replay over 4,818 recorded commands** from the audit log: one decision changed — an allow, a legitimate false positive removed. Zero new blocks.
- **Replay over 1,023 prose files** in the repository: 30 blocked before, 0 after.

Replay proves the fix did not break recorded behavior; it cannot prove no new smuggling shape exists. The must-block list is the contract, and it is only as complete as the shapes someone thought of.

## Lessons for agent-driven development

1. **Never use "contains" to grant an exemption over a shell command.** Establish that the command is *only* the exempt thing, or split it into clauses and evaluate each one.
2. **Separate "add scrutiny" and "skip scrutiny" uses of the same detector.** A loose match is safe in the first and a bypass in the second; give them different functions so the difference is visible in review.
3. **Replay the audit log against every guard change.** Thousands of real commands are a better regression suite than hand-written cases, and they catch the fix's own new mistakes — here, the heredoc allowlist.
4. **Fixing a false positive is a good time to find a false negative.** Both live in the exemption logic; read all of it, not just the branch that fired.
5. **A guard must never block the report about itself.** If it can, the defect report is the first thing lost.

Related: [PM-017](017-the-guard-that-suppressed-itself.md) (exemption matched the trigger), the [quoted-prose-stripping](../patterns/quoted-prose-stripping.md) pattern (mentions vs uses), [pretooluse-gate](../patterns/pretooluse-gate.md) (the mechanism), [PM-014](014-the-escape-hatches-that-never-existed.md) (bypass paths as a surface to audit).
