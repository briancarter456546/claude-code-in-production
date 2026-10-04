# File ownership between concurrent agent sessions followed the *tool*, not the writer — and the journal could not identify a write target in 94% of shell commands

**Keywords:** concurrent AI sessions file ownership, write journal shell command parsing, stranger file guard false positive, shell redirect not journaled, attribution follows the tool, wrong owner record not missing record, bash command write target inference, opaque command classification, guard bypass rate as bug report, multi-session attribution

**Incident date:** two instances 2026-09-28; rates measured over 2026-09-27 → 2026-10-04 · **Internal refs:** #2979, #2616, #2847 · **Status:** open — not fixed; ownership and claim semantics are inside a deliberate deferral boundary, and a containment directive is active on the adjacent claim route

---

## What broke

With 7–12 sessions in one working tree, this system records which session wrote which file, and a guard refuses to let a session commit or overwrite a file the journal attributes to **someone else** ([ADR-006](../adr/006-task-checkout-leases-and-collision-guards.md)). The record is the authority; the guard is only its enforcer.

The record was wrong in three distinct ways, and they degrade differently:

- **Owner silence (#2616).** Files written by a hook are never journaled at all. The next session to touch such a file becomes its *sole recorded owner* — not because it wrote the file, but because it is the only session the journal ever saw.
- **Legitimate work looking foreign (#2847).** The journal records the `Edit` and `Write` tools. Work done by running a script is not those tools, so a session's own output reads as a stranger's.
- **A positively wrong record (#2979).** The journaled `file_path` did not correspond to the command at all: **a `sed` invocation against one Python script was journaled as owning an unrelated review artifact.** This is the serious one. Owner silence is a gap and script work looking foreign is a classification error, but this is the journal *asserting* that a specific session owns a file that session never touched.

A second, independent instance the same day: the guard refused a test-output file, naming one session as its owner. A **different** session had created that file seconds earlier with a shell redirect (`pytest > file`). Both files were left on disk, uncommitted, with no bypass taken.

## How it was detected

By the guard working correctly on bad input. A session was refused access to a file it had just created, went to the journal to find out who the recorded owner was, and found a session that had never written it.

The workaround the refused session chose is the cleanest statement of the defect available: it **transcribed the content into a different file using the `Edit` tool**, because `Edit`-written files *are* journaled, and that file went through without complaint. The same bytes, authored by the same session, in the same second — admissible or inadmissible depending on which tool typed them. **Attribution followed the tool, not the writer.**

## Root cause

Ownership is inferred from tool-call metadata, which is reliable for `Edit`/`Write` (the harness states the path) and inferential for `Bash` (the path must be recovered by parsing a shell command). Shell is not parseable at that fidelity, and the journal's own classifier says so — honestly and loudly, in a field nobody was reading.

Measured over the 7-day window 2026-09-27 → 2026-10-04, the Bash-side journal ran **9,477 times**:

| classification | count |
|---|---|
| `opaque:unsupported_redirect` | 2,847 |
| `no_explicit_write_target` | 1,787 |
| `opaque:unproven_segment_execution` | 1,327 |
| `opaque:unparseable_construct` | 1,153 |
| `opaque:newline_list` | 1,012 |
| `opaque:hash_ambiguous_comment_or_word` | 555 |
| `opaque:tokenizer_failed` | 185 |
| `opaque:conditional_control_flow` | 60 |
| `opaque:unsupported_punctuation_run` | 3 |
| **journaled** | **519** |
| **parsed** | **18** |
| baseline_established / degraded | 7 / 4 |

**8,929 of 9,477 — 94.2% — ended with the journal unable to say what the command wrote. It identified a write target in 5.7% of shell commands.**

So the authority behind an ownership decision is, for shell work, almost entirely absent — and absence of a record does not read as "unknown" downstream. It reads as "not yours," or it leaves the last `Edit`-tool toucher as the only name on file.

The deeper cause is a mismatch between what the harness can observe and what the policy needs. The harness reports *tool calls*. The policy needs *writes*. Those coincide for two tools out of the set and diverge for the one that does most of the work in this repository.

## Blast radius

In the same 7-day window, the consuming guard ran **777** times: **300 blocks**, 328 clean allows, **69 bypasses**, 73 skipped for nothing staged, 7 skipped on an empty-journal bootstrap.

Those 300 refusals were issued against evidence that could name a shell writer 5.7% of the time. We are not claiming all 300 are false — a single sampled false positive is documented in #2979 and a second in its follow-up, and the rest are unadjudicated. That *is* the blast radius: **the population is unjudged, and the guard's own bypass rate is the only signal of friction anyone has been reading.** 69 overrides against 300 refusals is an 18.7% override rate on the refusal class, which under [ADR-017](../adr/017-bypass-rate-is-a-bug-report-on-the-guard.md) is a bug report filed against the guard, not against the sessions.

The harder cost is that the workaround is *cheaper than the correction*. Re-typing output through the `Edit` tool takes seconds and always works. A session that learns that trick stops hitting the guard, and the rate of false refusals drops — while the attribution data gets worse, because now the journal records a laundered write.

## The fix

**Not fixed.** Stated plainly because this repository's postmortems are not required to end in a repair:

- Ownership and claim semantics sit inside a deliberate deferral boundary set by the operator, and a **containment directive is currently active** on the adjacent route that lets a session establish a claim over a path it wrote. Under that directive, claim records must not be read as authorization evidence at all until the architecture gets independent review. Patching attribution while the consumer is contained would be building on a frozen foundation.
- The metadata correction on #2979 is worth recording as a small separate lesson: an attempt to link the three related tasks used a `link` subcommand that assigns a **strategy**, not a task relation, so one of these tasks carries a strategy id pointing at another task. The relationship had to be written in prose in the note instead.

What the record does establish, for whoever does fix it:

1. The three failure modes are **distinct** and need distinct handling. A missing record (#2616, #2847) can safely mean "unknown." A **wrong** record (#2979) cannot — it must be impossible to emit, or it poisons the authority.
2. `opaque` is already being computed and logged. The downstream guard does not consume it. Treating "the journal could not tell" as a first-class third state, rather than as absence, is a change to the *consumer*, and it is available without solving shell parsing at all.

## Has the guard fired since?

The guard fires constantly — 777 times in the measured week — and that is the problem rather than the reassurance. The relevant question for this postmortem is not whether it fires but **whether any of its 300 refusals have been judged correct or incorrect**, and the answer is that two have been examined and both were wrong. That is the same open hole named in [PM-066](066-the-shadow-gate-that-cannot-graduate.md): rows accumulate, nobody adjudicates them, and volume gets reported as if it were evidence.

## Lessons for agent-driven development

1. **An ownership system must distinguish "nobody wrote this" from "I could not tell who wrote this."** Collapsing the two into absence is what converts a parsing limitation into a false accusation.
2. **Never let an inferred attribution be *positive*.** A journal that guesses a path from a shell command may say "unknown"; it must not say "this session owns that file." A wrong name is worse than no name, because the enforcement downstream trusts names.
3. **If the cheap workaround launders the data, the guard is training the agent to corrupt the record.** Re-typing content through a journaled tool is faster than arguing with a refusal, works every time, and makes attribution permanently wrong. Watch for workarounds that *succeed quietly*.
4. **Measure your evidence source before you tune the enforcer.** The refusal rate looked like a concurrency problem. The 94% opacity rate says it is an observability problem, and no amount of tuning the guard fixes an input that cannot see.
5. **Attribution inherits the granularity of what the platform reports.** Here the platform reports tool calls and the policy wanted writes. When those differ, the policy will be enforced on the wrong axis — and the axis it is actually enforcing is the one to go find.
