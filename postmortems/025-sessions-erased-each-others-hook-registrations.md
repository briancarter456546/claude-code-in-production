# Parallel Sessions Overwrote Each Other's Hook Registrations — Twice in One Day

**Keywords:** settings.json race condition, hook registration lost, concurrent config writes, read-modify-write JSON, Claude Code settings, config file clobbering, last writer wins

**Incident date:** 2026-06 (twice in one day) · **Internal refs:** task #1321 · **Status:** mitigated (registration procedure + guard-side detection); the config file remains a shared-write hazard by platform design

---

## What broke

Claude Code hooks are registered in a JSON settings file in the repo (`.claude/settings.json`). Registering a hook means read-modify-write on that file.

Two sessions, same day, each installing or adjusting different hooks: session A read settings, session B read settings, A wrote (with A's new hook), B wrote (with B's new hook — **and without A's**, because B's in-memory copy predated A's write). A's hook registration vanished. Not disabled — *erased*, silently, by a sibling doing its own legitimate work. It happened again within hours in the other direction.

The insidious part: an unregistered hook doesn't error. It just stops being consulted. The enforcement a session believed it had shipped was simply *not there*, and nothing anywhere said so — the same silent-death signature as [PM-016](016-the-classifier-that-never-ran.md), via a different path.

## How it was detected

A guard that had verifiably fired earlier stopped firing; a session investigating found its registration absent from settings and, in git history, present-then-gone across a sibling's unrelated settings commit. The second occurrence same-day confirmed it as a race, not an accident.

## Root cause

**Unserialized read-modify-write on a shared whole-file config.** JSON files have no merge semantics; two writers with interleaved reads produce last-writer-wins with the loser's changes silently dropped. The platform's design assumes one editor of settings at a time — the same single-player assumption as the git index ([PM-011](011-bare-commit-swept-the-shared-index.md)) and the autocomplete history ([PM-024](024-ghost-text-from-another-session.md)), expressed in configuration.

The aggravator: hook registration is *infrastructure* work, exactly what multiple sessions were doing simultaneously during a guard build-out era.

## Blast radius

Two enforcement gaps of unknown duration (hours, by the timestamps); the audit cost of asking "which other registrations have we lost, ever?" — answered by diffing settings history against the hooks directory; and one more entry in the shared-mutable-state casualty list that eventually hardened the per-session-by-default rule ([ADR-014](../adr/014-per-session-skill-state.md)).

## The fix

Bounded honestly by what we control:

- **Procedure:** settings edits are claimed like any other contested file via checkout leases ([ADR-006](../adr/006-task-checkout-leases-and-collision-guards.md)) — the collision guard now covers config the same as code.
- **Detection over prevention:** a periodic self-test walks the hooks directory against the registrations and flags orphans in both directions (hook-without-registration, registration-without-hook). Lost registrations become a finding within a day instead of a mystery.
- **Not fixed:** the file itself remains whole-file read-modify-write — that's the platform's format. We serialize writers and detect losses; we can't give JSON a merge.

## Has the guard fired since?

The orphan-walk self-test has caught registration drift since (including one hook whose registration was lost to an *unrelated* settings rewrite — same mechanism, new trigger). The lease procedure has kept simultaneous settings edits from recurring; settings changes now show up in the checkout state every session sees.

## Lessons for agent-driven development

1. **Config files are shared mutable state — treat them with the same fear as the git index.** Any whole-file RMW under concurrency silently drops the slower writer's work.
2. **Registration-based systems need orphan detection.** Where "installed" means "listed in a file," build the walk that compares the list against reality on a schedule.
3. **Silent removal is worse than silent failure.** A hook that errors gets noticed; a hook that's no longer consulted just leaves you unprotected with full confidence.
4. **Infrastructure work clusters — and that's when the races hit.** The day everyone builds guards is the day guard registrations collide. Serialize the meta-work first.
