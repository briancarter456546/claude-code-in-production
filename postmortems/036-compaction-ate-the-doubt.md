# The Agent Flagged Its Own Result as "Too Good to Be True" — Then Compaction Deleted the Doubt

**Keywords:** context compaction memory loss, LLM long session degradation, too good to be true backtest, confidence laundering, unsourced number hardcoded, skepticism decay, context window compaction risks

**Incident window:** 2026-07 (exhibits B8, B1 from the degraded-window review) · **Internal refs:** degraded-window step-3 findings; recording-layer gates · **Status:** mechanism confirmed; fixes at the recording layer (doubt must be durable)

---

## What broke

Two exhibits from the same systematic review, both with turn-level receipts:

**Exhibit 1 — doubt, compacted.** A session produced a backtest result so strong it said so itself: at turn 7, it called the numbers (Sharpe ~4.4, triple-digit growth) *"almost certainly too good to be true"* — the correct instinct. At turn 8 it looked briefly, found nothing, and said "no bug found." **At turn 10 the context compacted.** The compaction summary preserved the *numbers* — clean, quotable, spreadsheet-shaped — and dropped the *doubt*, which was hedged prose. Every turn after, the session treated the result as established, and it was eventually recorded at maximum confidence. The mechanism was later confirmed as a genuine simulator flaw (cost-free daily rebalancing — the too-good was too good). The agent had *caught it* — and then forgot it had, because **compaction is a summarizer, and summarizers keep conclusions, not reservations.**

**Exhibit 2 — the number that outlived its refutation.** A session answered the operator's direct "does this beat the benchmark?" with a growth figure (17.92%) — which the *same session* re-derived four turns later at 13.29% (below the benchmark), without ever retracting the first answer. Its own turn-11 note had already flagged the 17.92% as provenance-free. The unsourced figure survived anyway — **hardcoded into a dashboard's source** as a constant, where a review later found it presiding over production like a fact.

Related, same era: a session that made *seven* compactions introduced a subtle future-data bug into a live dashboard while fixing something unrelated — long-degraded sessions don't just lose doubt, they lose the invariants they'd been holding.

## How it was detected

The degraded-window review: re-reading sessions turn-by-turn against their own later states. That method — *diff the session against itself across compactions* — is the reusable detector; nothing real-time caught either exhibit.

## Root cause

**Skepticism is stored in the most compressible part of the context.** Numbers are compact, declarative, and survive summarization; doubt is discursive, hedged, and gets summarized away. Every compaction is therefore a one-way valve toward confidence. Combine with anchoring (the first number said aloud becomes the number) and you get confidence laundering by pure mechanics — no motivated reasoning required.

## Blast radius

One maximum-confidence false finding recorded (later corrected via the KB's supersession chain); one fictional constant shipped into a production dashboard; and the general write-down of every long-session conclusion produced across a compaction boundary during that era.

## The fix

Doubt was made *durable* — moved out of the context window into stores compaction can't touch:

- **Unresolved flags are records, not prose:** "too good to be true," "provenance unknown," and kin are written to the session's checkpoint/notes files as structured open items the moment they're uttered; wrap procedure refuses to close over open integrity flags.
- **The recording layer became the skeptic** ([PM-013](013-integrity-ledger-certified-fabricated-results.md)): findings headed for the knowledge base face recomputation gates that don't care what the session currently remembers believing.
- **Numbers entering dashboards/code need cited provenance** — the hardcoded-constant path specifically now trips review (an unsourced numeric literal in a data surface is a finding by definition).

## Has the guard fired since?

The recording-layer gates are the active enforcement (their own scorecard lives in PM-013). The durable-doubt discipline shows up in session artifacts — open-item blocks surviving compactions they would previously have died in. Honest note: "wrote the doubt down" depends on the moment of doubt producing a write; the residual gap is real and named.

## Lessons for agent-driven development

1. **Compaction keeps conclusions and deletes reservations — by construction.** Any doubt that lives only in conversational context has a half-life of one summary.
2. **Write skepticism to disk the moment it exists.** A structured open-items file is the difference between "the agent caught it" and "the agent once caught it."
3. **First-said numbers anchor; retractions don't propagate.** A later correction must hunt down every place the first number landed — or the recording layer must stop unsourced numbers from landing at all.
4. **Count compactions as a risk metric.** A seven-compaction session is not the session that started; treat its outputs to fresh-context review before they touch anything durable.
