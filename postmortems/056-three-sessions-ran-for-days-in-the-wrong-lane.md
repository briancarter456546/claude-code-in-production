# Three sessions ran for days under the wrong work lane: one shared marker let every concurrent session re-stamp everyone's context

**Keywords:** concurrent Claude Code sessions, shared state file last writer wins, per-session state, prompt classifier, context injection wrong domain, UserPromptSubmit hook, session marker file, lane routing, silent misroute, dead hook env var

**Incident date:** misroutes 2026-09-05 to 2026-09-10; root cause confirmed and fixed 2026-09-10 · **Internal refs:** #1291, #2709, #2712, #2715 · **Status:** fixed (per-session lane, acceptance-tested); the underlying refactor task had been open since 2026-05-22

---

## What broke

Every session in this system works inside one **lane** — trading, infrastructure, content, the speaking business, and so on ([ADR-004](../adr/004-lane-discipline-for-concurrent-sessions.md)). The lane decides what gets pushed into the agent's context on every prompt: which knowledge-base findings, which "never revisit these" rules, which methodology reminders, and what the session's notes file is named.

Three sessions doing non-trading work — a client keynote event, an income-product brainstorm, and a one-man-show plan — ran **under the trading lane for their whole lives**, between one and five days each. All three notes files were created with a `trading_` filename prefix and a `Lane: trading` header. Every prompt injected the dead-trading-systems rule block into sessions about joke templates and event logistics, while nothing relevant to their own work was injected at all.

Nothing errored. The context was *plausible* — it was real, correct knowledge about the wrong subject — so neither the agent nor the operator read it as a fault.

## How it was detected

Not by a guard. The operator noticed a behavior, not a label: one of the sessions had spent four days creating about ten standalone markdown files and **never once queried or wrote the knowledge base**. The operator's correction: *"you keep creating new files for things, which other sessions won't even know about — of course KB is the solution."*

Tracing why the knowledge base never came up led to the lane, and a follow-up audit found the other two sessions carrying the same wrong header.

## Root cause

Two pieces of state that should have been per-session were global.

**1. The lane lived in one shared state file.** A first-prompt hook classifies the session's lane by keyword and writes it to a single state file every other hook reads. With 7–12 sessions open, that file holds whichever session wrote last. The notes-file hook, for instance, reads it at session start — *before* the new session's prompt has been classified at all — so it stamps the previous writer's lane. This was a known defect: a task to make that file per-session had been open since May.

**2. The "have I already classified?" marker was also one shared file** — and this is the part the May task had not named. The classifier guarded itself with a marker holding *the last session id that classified*. Session B's first prompt overwrote it. Session A's next prompt saw a mismatch, concluded it had never classified, and re-classified — from a later prompt, not its first one. Any later prompt that happened to mention a trading word (a ticker, "backtest") flipped the global lane to trading **for every reader in every session**.

So the marker designed to make classification happen once per session made it happen on nearly every prompt, in whichever session typed last.

**Compounding it, found in the same audit:**

- **The domain-document injector had been dead for eight weeks.** It read the prompt from an environment variable the harness never sets and discarded the stdin payload where the prompt actually arrives. Its last real injection in the audit log is 2026-07-15. That is the exact defect of [PM-016](016-the-classifier-that-never-ran.md) — fixed in the classifier back then, never checked for in its sibling.
- **The knowledge base could not hold these lanes' findings.** Its domain field is a closed list of four values; three active lanes had **zero** nodes each because recording one required a code edit. Session-start context was hard-coded to the trading domain regardless.

## Blast radius

- Three sessions, roughly one to five days each, received another lane's rules on every prompt and none of their own.
- One of them produced about ten files other sessions cannot discover, where the shared store was the right home — the operator's four-day correction.
- Recording the brainstorm's findings afterward required filing them under the wrong domains with tags, because the right domains did not exist.
- No trading decision was affected: the misroute ran in the other direction, trading context into non-trading work.

Confidence note from the internal audit, kept here: the misroute itself is certain (three notes headers); the exact interleaving that flipped each session is inferred from the code, because the classifier did not log its decisions per session.

## The fix

- **Lane is per-session.** It lives in the session's own state file, keyed by session id; the global file is kept only as a mirror for legacy readers and is never blanked. A query command returns *this* session's lane, and the project instructions now tell sessions to read that, never the mirror.
- **Idempotency is per-session too.** The "already classified" check reads the session's own file, so another session's first prompt cannot reset it.
- **The classification is printed** as a visible line in the first prompt's context, with its source (keyword, declared, default), so a wrong lane is seen on turn one instead of inferred on day four.
- **Session-start knowledge context follows the lane** instead of a hard-coded domain, and the notes file starts with a neutral `pending_` name that is renamed once the session's own lane is known.
- **Two new lanes and their canonical paths** were added to the write guard, and 112 previously file-only content rules were seeded into the knowledge base where sessions can reach them.

Acceptance test before commit: **60 checks, 0 failures** on fake session ids, including two concurrent sessions keeping distinct lanes and a trading-worded second prompt leaving a non-trading session's lane unchanged.

Not fixed in the same change, tracked separately: roughly 29 older shell hooks still read a profile field from the shared file (their gates were already always open, so they are inert rather than wrong), the dead domain injector, and the closed domain list.

## Has the guard fired since?

The fix passed its 60-check acceptance test and is live; no post-fix misroute has been reported in the three days since. There is no guard that *blocks* on a wrong lane; detection is now a human reading one line on turn one. That is a deliberate choice, not a proof: whether a misclassification gets noticed at turn one rather than day four has not yet been tested by a real misclassification.

## Lessons for agent-driven development

1. **A shared "have I done this yet?" marker is a race, not an idempotency check.** Under concurrency, "the last id that did it" means "some session did it recently," and every other session reads that as "not me."
2. **Plausible wrong context is invisible.** Injection that is correct about the wrong subject raises no error and reads as helpful. Print what was routed and why, where a human will see it.
3. **When you fix a defect class in one hook, grep its siblings the same day.** The env-var-never-set bug was fixed in the classifier two months earlier; the injector beside it kept the bug and went silent.
4. **A closed enum in the memory layer silently decides which work can be remembered.** Three lanes had zero findings not because nothing was learned but because recording it required editing code.
5. **"Per-session by default" is a rule you have to re-apply to every new piece of state.** This system adopted it after [PM-022](022-two-sessions-one-identity.md); the lane and its marker were written before, and nobody went back.

Related: [PM-022](022-two-sessions-one-identity.md) (the shared-file clobber class), [ADR-014](../adr/014-per-session-skill-state.md) and the [per-session-state](../patterns/per-session-state.md) pattern (the rule this violated), [context-injection](../patterns/context-injection.md) (the mechanism that delivered the wrong context faithfully).
