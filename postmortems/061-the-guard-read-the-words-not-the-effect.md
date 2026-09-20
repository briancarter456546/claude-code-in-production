# Our destructive-action guard scanned for scary words, so a silent file truncation passed and a report about it was blocked

**Keywords:** destructive action guard false negative, keyword matching guard, PreToolUse content scan, file truncation not detected, agent overwrote file silently, guard blocked its own bug report, effect-based vs text-based enforcement, size drop check, split string literals to avoid self-match, data loss by rewrite

**Incident date:** 2026-09-16 · **Internal refs:** #2789, grid #2776 · **Status:** effect-based truncation check shipped 2026-09-17; the text-pattern guard is unchanged and still the first line

---

## What broke

The oldest guard in this stack blocks destructive actions. It works by scanning the text of a tool call for destructive things: row-deletion and table-drop statements, recursive directory removals, unlink calls, force pushes.

Two probes from the coverage audit in [PM-060](060-we-measured-which-destructive-actions-our-hooks-actually-block.md) hit it from opposite directions and both landed:

- **A write that replaced a 27,970-byte hand-written reference document with 30 bytes was allowed.** Destroying the file was the entire content of the operation, and the guard saw nothing destructive, because the replacement text contained no destructive keyword. There is nothing to match. That is what makes it silent.
- **The same guard blocked the audit's own report** — a prose document — because the report quoted a row-deletion statement while explaining the first failure.

One mechanism, both failures. The guard was asking "does this text look alarming?" when the question is "what does this operation do to the file?"

## How it was detected

By the probe harness described in [PM-060](060-we-measured-which-destructive-actions-our-hooks-actually-block.md), not by a data loss. The truncation probe was written to test exactly this: an operation with maximum effect and minimum alarming vocabulary.

The false positive was not designed. It happened while writing up the false negative, which is the same shape as [PM-059](059-the-exemption-was-inherited-by-the-whole-command.md) — a guard blocking the document that reports on the guard.

Then it happened twice more, to this file. Publishing this postmortem took three attempts: the first draft was refused by the guard it describes, for quoting one of that guard's patterns, and the second by a *different* content guard, for a sentence in which two ordinary English words happened to sit next to each other in the order an attack-vocabulary expression looks for. Neither refusal was about anything this file does. **Writing up a content guard is reliably blocked by content guards.**

There is a fourth piece of evidence, and it was sitting in the guard's own source the whole time. Its pattern catalog is written as **split string literals** — each pattern is assembled from two fragments at import time. The reason is that a guard which scans text for a phrase will match its own source file. The authors had already been forced to obfuscate the guard from itself. **That workaround is the defect, stated in code:** a tool which cannot contain the words it looks for is matching vocabulary, not behaviour.

## Root cause

**Text is a proxy for effect, and the correlation is weak in both directions.**

- Weak as a detector: a write, a redirect, or an interpreter call can destroy a file without naming the act. The most destructive operation available — replacing a file's whole content — is carried in the write's content field, which is arbitrary text and looks like every other write.
- Weak as a filter: humans and agents legitimately *write about* destructive operations all day. Reports, postmortems, plans and bug filings quote the commands they discuss. To a vocabulary matcher, a report about a deletion and a deletion are the same string.

The deeper cause is what the guard has access to. A content scan sees the incoming text. To judge effect it needs the **before state**: what is on disk now, how large it is, whether anyone wrote it by hand. None of that was in the comparison.

## Blast radius

**No document was lost.** The truncating probe targeted a decoy path and nothing executed.

The unmeasured exposure is the one that matters: for as long as the guard has existed, the operation "rewrite a hand-authored file down to nothing" has been unguarded, and it is an ordinary thing for an agent to do by accident — a partial regeneration, a template write against the wrong path, a patch that turns into a replacement. Nothing in the audit log records such a write, because nothing was watching for one; absence of evidence here is exactly that.

The false-positive side has a measured cost elsewhere: guards that block prose train sessions to route around them ([PM-021](021-alarm-fatigue-by-the-numbers.md)).

## The fix

- **A size-drop check that ignores text entirely.** On a write to a document-like path, compare the bytes already on disk against the bytes about to be written. Refuse when an existing file of at least 2,000 bytes would shrink to under a quarter of its current size. The refusal message states both numbers and names what it thinks is happening: a rewrite over someone's work, not an edit.
- **Generated and fixture paths are excluded by path pattern**, because shrinking a regenerated artifact is normal and shrinking a hand-written document is not. The distinction the guard needed was never about the words — it was about who authored the file.
- **The threshold is a ratio plus a floor, not a keyword list**, so it cannot be dodged by phrasing and does not fire on small files where a large relative shrink is routine.
- **The text-pattern guard stays.** It catches shell-shaped destruction that never reaches a write at all. The two are complementary; the mistake was believing the first one covered the class.
- **Bypass is a single named environment variable**, logged as a bypass with the same byte counts, so deliberate truncations are recorded rather than invisible.

## Has the guard fired since?

**26 truncation refusals are recorded between 2026-09-17 and 2026-09-20 — and every one of them is a probe or self-test**, identifiable by their decoy targets and by the fact that they repeat. Two representative pairs: 27,970 bytes to 30, and 8,482 bytes to 5.

So: the check is wired, reachable, and computes the comparison correctly on real byte counts. **It has caught nothing in production yet, and it is therefore still a hypothesis** — worth saying out loud, because the failure it addresses was invisible for months and will stay invisible if this guard is quietly broken. The honest status is "instrumented", not "solved". Guards here are graded against their own fire logs ([ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md)), and this one has not yet produced a log worth grading.

## Lessons for agent-driven development

1. **Guard the effect, not the vocabulary.** For file writes, the effect is computable and cheap: size before, size after, is the target hand-authored. For a database, it is the row count. Compare states; do not read strings.
2. **If your guard needs to hide its own patterns from itself, it is matching the wrong thing.** Split string literals in a pattern catalog are a self-diagnosis sitting in the source.
3. **Text matchers fail in both directions at once, and the two failures are the same bug.** Do not fix the false positive without looking for the false negative in the same expression — they share a cause.
4. **The most destructive operation an agent performs is usually an ordinary-looking write.** Deletion is conspicuous and gets guarded. Replacement is not, and is far more common.
5. **"Nothing in the log" is not evidence when nothing was logging.** Instrument first; only then is the empty count meaningful.
6. **Documentation about your guards is the highest-density false-positive source you have.** Every incident report quotes the thing it reports on. If writing up an incident is blocked by the guard the incident is about, the guard is scanning the wrong layer — and the write-up is the cheapest test case you will ever get.
