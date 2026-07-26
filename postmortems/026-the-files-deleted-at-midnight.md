# Session Notes Deleted Mid-Session by an Unknown Actor — Twice, Both Times Across Midnight

**Keywords:** unexplained file deletion, unattributable failure, date rollover bug, session notes loss, untracked file deletion, forensics without provenance, unsolved incident

**Incident dates:** two occurrences ~24h apart, 2026-07-15/16 · **Internal refs:** task #2066; degradation plan §3.5 · **Status:** OPEN — root cause never established; published as the honest specimen of the unattributable class

---

## What broke

Two independent sessions, about 24 hours apart, had **untracked files under `notes/` deleted while the sessions were live.** One session ended the day with *zero* notes files — everything it had written to its own session log, gone. Both losses straddled midnight.

Untracked means untracked: no git history, no object store, no recovery. The files' only existence was the working tree, and the working tree said no.

This entry is in the public record for an unusual reason: **we never found the cause**, and a failure record that only contains solved cases is lying by omission about what production is like.

## How it was detected

The owning sessions noticed their own absence of state — a notes file that had been appended to all day failing to exist at the next append. Because per-session notes filenames embed session IDs, the missing set was precisely enumerable; because they were untracked, that enumeration was also the complete list of what could ever be known about their contents.

## Root cause

Unknown. The honest shortlist, none confirmed:

- **Date-rollover logic** in the notes-persistence path (both incidents crossed midnight; filename patterns embed dates; a "yesterday's file" cleanup or rename-miss could delete rather than roll) — the leading suspect, investigated, not caught in the act.
- **A sibling session's cleanup** — some sessions run scratch-file hygiene; none logged a deletion matching these paths, but not all deletion paths were logged then.
- **A hook acting on stale state** — several hooks write/manage notes; each was audited for deletion-capable code; two candidates were hardened on principle without evidence of guilt.

What the investigation *did* establish: no `git clean` in any session's command record, no relevant cron on the machine at those hours, and no matching pattern since the hardenings below.

## Blast radius

Two sessions' working notes lost irrecoverably; a permanent hole in the session-history record for those days; and disproportionate investigative cost — unattributable incidents consume more forensic hours than solved ones precisely because nothing rules anything out.

## The fix

Fixes for a cause you haven't found are really *containments*:

- **Notes became less deletable:** persistence path hardened around the midnight boundary (roll-forward never deletes; renames are copy-then-verify-then-remove).
- **Deletion got provenance:** file-removal operations in hook-controlled paths now log actor, path, and reason to the append-only audit trail — the next occurrence will at least name its perpetrator.
- **Notes worth keeping get committed sooner:** wrap procedure pushes notes into git earlier, shrinking the untracked exposure window that made this unrecoverable.

## Has the guard fired since?

The deletion-provenance log has recorded routine, legitimate removals since — and no recurrence of the midnight pattern. Which proves containment, not understanding: the difference matters and we decline to blur it.

## Lessons for agent-driven development

1. **Some failures in multi-agent systems are unattributable with the logging you have** — and that's a property of the logging, not of the universe. Provenance-on-deletion should predate the first mystery, not follow it.
2. **Untracked files are one actor away from never having existed.** Anything a session would mourn belongs in git within minutes, not at wrap.
3. **Boundary times are bug magnets.** Midnight, month-end, DST: anything that embeds dates in filenames deserves adversarial review at the rollover.
4. **Publish your unsolved cases.** A postmortem culture that only ships tidy root causes trains readers to expect attribution that production doesn't always offer — and trains writers to invent it.
