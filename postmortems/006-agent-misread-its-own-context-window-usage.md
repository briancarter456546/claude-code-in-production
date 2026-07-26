# Our AI Agent Read Its Context Window at 17% Full — It Was at 85%

**Keywords:** Claude Code context window, LLM context management, context compaction, agent self-assessment, session wrap-up, long-running AI sessions, context usage measurement

**Incident window:** 2026-07 · **Internal refs:** task #2071; KB nodes 46148, 45831 · **Status:** fixed (measured injection); zone scheme active in every session

---

## What broke

Long-running agent sessions need to wrap up — commit, write a handoff, persist state — *before* the context window fills and the work degrades. Our wrap policy asked the agent to track how full its window was.

A session estimated itself at roughly 17% of its context window. It was actually around 85% — past every danger threshold we'd defined, into the zone where the next big file read triggers compaction and silently deletes working memory. The session sailed on, confident, with no wrap warning of any kind. The estimate wasn't slightly off; it was inverted.

## How it was detected

The session hit degradation symptoms (compaction, lost thread-of-work) that its own self-report said were impossible, and the post-incident review compared the self-estimates against the harness's actual token accounting. The gap was not subtle: the model had no functional access to the quantity it was confidently reporting.

## Root cause

**A language model cannot see its own context occupancy.** There is no introspective channel to the harness's token counter. Asked anyway, the model does what models do: produces a fluent, confident number derived from narrative cues ("we've done a few things, feels early"). A long session with many small turns *feels* identical to a long session with a few enormous tool results — but only one of them is nearly full.

The deeper cause was a design assumption that "the model can estimate X" is a reasonable default for any X. For harness-level quantities, it isn't — it's an invitation to confident fiction.

## Blast radius

Sessions ran past safe wrap points without warning; at least one lost working state to compaction that a timely wrap would have preserved. A related false KB entry about context-window size (see [PM-005](005-false-finding-sat-in-knowledge-base-six-weeks.md)) compounded the confusion during diagnosis — the recorded "spec" the estimates were checked against was itself wrong for weeks.

## The fix

Remove the model from the measurement loop entirely:

- The harness/hook layer computes **context-used percentage** from actual token accounting and **injects the number into the session's status loop every turn**. The model consumes the measurement; it never produces it.
- Fixed zones with defined obligations replace vibes: under 50%, work normally (wrap-up may not even be suggested — see [PM-007](007-wrap-nudge-overfiring-below-half-context.md) for the opposite failure); 50–70%, draft the handoff alongside the work; 70–85%, wrap and commit; above 85%, stop and hand off.
- When the measured ceiling changed with a model upgrade, the *denominator* was updated in one place — the injection source — rather than in anyone's beliefs.

## Has the guard fired since?

The zone scheme runs in every session; the injected percentage appears in each turn's status block, and multi-day sessions now routinely wrap in the 70–85% band with intact handoffs. The failure mode this postmortem describes — a confident self-estimate diverging from reality — is structurally gone, because there is no self-estimate anymore.

## Lessons for agent-driven development

1. **If the harness can measure it, inject the measurement. Never ask the model to introspect it.** Context usage was our first catch; the rule generalizes to time, cost, token spend, and anything else the runtime knows and the model doesn't.
2. **Confident fiction is the failure signature of unmeasurable questions.** The model won't say "I can't know that" — it will say "17%."
3. **Proxies fail in both directions at once.** Turn counts and wall-clock age were uncorrelated with actual context pressure; both over- and under-triggered. One measured number replaced them all.
4. **Schedule the choice of what survives.** Compaction decides what to forget without asking. A zone-scheduled wrap is the operator choosing, while good context still exists, what the next session inherits.
