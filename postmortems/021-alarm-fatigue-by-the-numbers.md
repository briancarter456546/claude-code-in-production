# Alarm Fatigue, Measured: One File Approved 25 Times, 70k Tokens of Guard Retry Churn

**Keywords:** alarm fatigue automation, guard friction cost, hook false positive burden, AI agent retry churn, context pollution, approval fatigue, guardrail UX, compaction poisoning

**Incident window:** measured 2026-07-16 (degradation analysis) · **Internal refs:** #1794; designer-ack v2.3; session-degradation plan §0.0–0.1 · **Status:** fixed per-guard (creation-only gating, once-per-session nags); the measurement method is the artifact

---

## What broke

No single guard misfired. The *sum* of correctly-firing guards became a failure mode of its own. Three measured exhibits:

- **One in-development file was approval-gated 25 separate times.** The designer-ack gate (new tools require answering design questions — [ADR-011](../adr/011-designer-ack-and-seven-question-design-gate.md)) used a TTL-bounded marker and re-gated on *every edit* of an untracked file. A developer iterating on a new script re-answered the same approval for the same file, 25 times. By approval #6, answers are pasted; by #12, the ritual is noise; the gate has trained its audience to rubber-stamp — the exact behavior it exists to prevent. A companion audit counted **536 human bypasses** of the same guard fleet-wide; root cause wasn't scope, it was *re-acking*.
- **One session absorbed 72 guard blocks — ~70,000 tokens of block-message boilerplate and retries.** A mandatory-checkout gate (78 blocks / 11 allows fleet-wide in the window; 72 in a single session) repeatedly blocked writes while the session negotiated scope. The token cost wasn't just latency: **guard boilerplate dominated the transcript, so when the context window compacted, the summary preserved guard noise at the expense of work state.** The enforcement layer was curating what the agent remembered — badly.
- **A session-start advisory injected itself into every prompt** for the rest of the session after its 5-minute warmup, having been designed as a one-time nudge.

## How it was detected

Deliberate measurement during a session-degradation investigation: token accounting by source (whose text fills the window?), fire-count tables per guard, and the 25-ack outlier surfacing from marker-file timestamps. None of it was visible as an *event* — only as arithmetic.

## Root cause

Guards were designed one at a time against the question "does this stop the bad thing?" — never against "what does this cost per week, multiplied by every session, and what does the *ensemble* do to attention and context?" Alarm fatigue is an emergent property; no individual guard owns it, so without an ensemble-level audit, nobody does.

## Blast radius

Rubber-stamping behavior on a gate that guards design quality; measurable context-window pollution feeding compaction loss; and background desensitization that taxes every *other* guard's credibility (the wolf-crying problem — see also [PM-007](007-wrap-nudge-overfiring-below-half-context.md)).

## The fix

- **Designer-ack became creation-only:** gate the birth of a new artifact, not every subsequent edit. Ack count per file dropped to one.
- **Nags got budgets:** once per session, not once per prompt.
- **Block messages got a size discipline** and blocked-retry loops a circuit-breaker mindset: a guard that blocks the same session repeatedly should escalate to a human-readable summary, not re-print the same 900-token banner.
- Ensemble accounting joined the standing gate audit ([ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md)): per-guard fire counts, bypass rates, and token cost, reviewed together.

## Has the guard fired since?

The *audit* has: the fire-count and bypass tables in this repo's postmortems come from it. Re-ack counts collapsed after creation-only gating; the every-prompt nag is verifiably once-per-session in the logs.

## Lessons for agent-driven development

1. **Correct guards, summed, can be a bug.** Audit the ensemble — total blocks, total tokens, total acks per week — not just each guard's logic.
2. **Repeated approval requests train rubber-stamping.** Gate creation, not iteration; an approval that recurs identically is friction, not scrutiny.
3. **Block messages compete with work for context.** In LLM sessions, guard verbosity isn't just annoying — it poisons what survives compaction. Boilerplate is a memory tax.
4. **Watch bypass and re-ack counts as leading indicators.** 536 bypasses and a 25-ack file were visible in the data long before anyone felt the pain consciously.
