# A False "Fact" Sat in Our AI Agent's Knowledge Base for Six Weeks — and Human Review Didn't Catch It

**Keywords:** LLM confabulation, AI agent knowledge base, false memory, human-in-the-loop review, contradiction detection, knowledge base curation, agent long-term memory, confidence scores

**Incident window:** ~6 weeks through 2026-07; ack policy revised 2026-07-17 · **Internal refs:** KB node 45831; curator spec §1b · **Status:** fixed; the curator's contradiction scan now fires routinely (25 out-of-policy write attempts caught in a recent 12-day window)

---

## What broke

The system keeps an append-only knowledge base — the agent's long-term memory, whose entries outrank the model's priors by policy. An entry was seeded claiming a specific (wrong) context-window size for the then-current model. It carried a healthy confidence score, sat unchallenged for six weeks, and fed a downstream session-management rule the whole time: wrap-up behavior was being tuned against a hardware limit that didn't exist.

The dangerous part isn't that a false entry existed. It's that the entry passed **human review on the way in**. Every knowledge-base write at the time required an operator acknowledgment. The ack was granted — plausible-sounding entries get acked, that's what plausible means.

## How it was detected

Not by a person. The knowledge base's curator agent — the single mediator through which all KB writes route — runs a **contradiction scan** on incoming writes against existing validated entries. A later, correct entry about the model's context handling collided with the false one, and the scan flagged the conflict. Six weeks of human eyeballs had passed over the claim; one automated cross-reference caught it.

## Root cause

Two mechanisms, stacked:

1. **Confabulation is fluent.** The false claim was exactly the kind of thing that *could* be true — a plausible spec for a real model. Nothing about it pattern-matched to "suspicious." Human review filters for implausibility, and confabulation's defining feature is plausibility.
2. **The review step had no leverage.** The operator acking a KB write sees the claim, not the claim's relationship to everything already recorded. The contradiction scan sees exactly that relationship. The safeguard with the information advantage was running *after* the safeguard without it — and the one without it was the mandatory gate.

## Blast radius

One downstream operational rule tuned against a fictional constraint for six weeks. No data loss; the real cost was trust calibration — the discovery forced an audit stance toward every entry that had entered through the same door, and it permanently changed what the human ack is trusted to catch (see below).

## The fix

The entry was superseded, not deleted — the KB is append-only, so the wrong claim remains visible with its correction chained on top. The evidence trail of being wrong is part of the record.

The structural fix was the interesting one: **the blanket human ack was narrowed, not expanded.** Post-incident policy (2026-07-17): the curator writes genuinely *new* findings directly; human acknowledgment is reserved for supersessions, contradictions of validated entries, and forced writes — the cases where the contradiction scan has already raised its hand. Rationale, recorded at the time: the blanket ack demonstrably caught nothing (it approved this very entry), while the automated scan was doing the real catching. Spending scarce operator attention where evidence showed it didn't help was a cost with no benefit.

## Has the guard fired since?

Yes, in two senses. The contradiction scan runs on every curator write and periodically flags collisions for human arbitration — those are its designed catches. And the write-path enforcement around the curator (any KB write attempted *outside* curator context is logged as a policy violation) caught 25 out-of-policy write attempts in a recent 12-day audit window. The door has traffic; the lock matters.

## Lessons for agent-driven development

1. **Human review of agent memory writes filters for implausibility — and confabulation is plausible by construction.** The review step everyone reaches for first is nearly blind to the failure mode it's meant to stop.
2. **Give the veto to the process with the information advantage.** A contradiction scan sees the claim against the whole record; a human ack sees the claim alone. Order your gates accordingly.
3. **Append-only memory turns errors into evidence.** Because nothing is deleted, the false entry, its six-week tenure, and its correction are all still inspectable — which is what made this postmortem writable.
4. **When a safeguard catches nothing, narrowing it is the fix, not heresy.** Measure what each gate actually catches. Ritual checks aren't neutral; they spend the attention that working checks need.
