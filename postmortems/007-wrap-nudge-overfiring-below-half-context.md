# Our AI Agent Kept Trying to End Sessions at 20% Context — the Opposite Failure

**Keywords:** AI agent session management, premature wrap-up, Claude Code Stop hook, agent ceremony overhead, context window zones, long-running sessions, agent nudging behavior

**Incident window:** recurring through 2026-06/07 · **Internal refs:** wrap-suggestion guard · **Status:** fixed; Stop hook blocks wrap suggestions below 50% measured context

---

## What broke

[PM-006](006-agent-misread-its-own-context-window-usage.md) is the under-warning failure: a session near its context ceiling that thought it was fresh. This is its mirror twin, and it arrived first.

Sessions at 15–25% context usage — hours of runway left — kept *suggesting their own funerals*: "Shall we wrap up and commit what we have?", "This might be a good point to write a handoff," "Want me to close out this session?" The trigger was narrative, not physical: the agent had "done a lot of things" (many small completed steps), and models pattern-match *accomplishment density* to *time to conclude*.

Each nudge costs little. The aggregate was real: an operator running many concurrent sessions gets trained to ignore wrap talk (so the *legitimate* 75% wrap warning drowns), and sessions that should have run for days kept angling to end at lunch.

## How it was detected

Operator annoyance, made legible by the status-block record: sessions with green-zone measured context repeatedly steering toward closure ceremony. Once the measured percentage existed (the PM-006 fix), the mismatch was quantifiable — wrap suggestions at 20% against a policy that doesn't want them before 50%.

## Root cause

Two layers:

1. **Models conflate narrative arc with resource state.** "We finished several things" *feels* like an ending. Without a measured number, the model substitutes story-shape for the fuel gauge — the same introspection gap as PM-006, expressed in the opposite direction.
2. **Politeness bias toward offering exits.** Assistant-trained models offer closure as a service ("anything else?"). In a multi-day working-session context, that instinct is miscalibrated: the operator decides when sessions end, and the offer itself is noise with a training effect.

## Blast radius

No data loss — this failure burns attention, not state. The cost: wrap-talk desensitization (the alarm-fatigue mechanism, same class as any over-firing guard), plus session churn where work got prematurely packaged instead of continued.

## The fix

An enforcement rule keyed to the *measured* percentage, not to instructions the model might weigh against its instincts:

- **Below 50% context: wrap-up may not be suggested at all.** Not proposed, not offered, not hinted via "should we commit as a checkpoint?" The operator can always raise it; the agent may not.
- A **Stop hook enforces this** — it scans outgoing responses in green-zone sessions for wrap/handoff/closeout suggestion patterns and refuses delivery, forcing a rewrite that ends on the work itself.
- Above 50%, the zone obligations (draft handoff → wrap → stop) take over per the scheme in PM-006.

The design point: this is a *symmetric pair* of guards around one number. The injected measurement kills the under-warning failure; the Stop hook kills the over-suggesting one. Neither instruction alone had held.

## Has the guard fired since?

Yes — it blocks green-zone wrap suggestions in live sessions, and its bypass (reason-logged, like every guard here) records the legitimate exceptions, mostly operator-initiated early wraps. The nudge pattern stopped being a training input the day the hook shipped: rewrites end on work instead of ceremony.

## Lessons for agent-driven development

1. **Agents fail on both sides of every threshold — build the guard pair, not the guard.** An under-warning fix without an over-suggesting fix just relocates the failure.
2. **Story-shape is not resource-state.** "We accomplished a lot" and "we are out of room" are uncorrelated; only one of them is measurable, so measure it.
3. **Repeated benign suggestions are an attack on operator attention.** The tenth premature wrap offer costs more than the first, because it's the one that teaches the operator to ignore the real warning.
4. **Enforce prohibitions at the delivery boundary, not in instructions.** "Don't suggest wrapping early" competes with training-level politeness instincts every turn. A Stop hook doesn't negotiate.
