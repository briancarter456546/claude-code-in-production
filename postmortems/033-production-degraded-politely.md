# Production Degraded Politely: a Cron That Never Once Succeeded, a WARNING That Lasted Six Days

**Keywords:** silent production degradation, cron never succeeded, OOM killed cron, warning fatigue logs, non-fatal error invisible outage, cron dependency ordering, stale data pipeline

**Incident window:** three exhibits across 2026-04→07 · **Internal refs:** tasks #1177, #2085/#2082; migration review (OOM) · **Status:** two fixed, one (host migration) tracked; drift detectors now emit hundreds of findings

---

## What broke

Three separate incidents, one law: **production systems that degrade without failing produce outages nobody schedules a response to.**

- **Exhibit A — the dashboard built from yesterday (task #1177):** the morning dashboard cron ran *before* the daily price update for weeks. Every stage green; every morning's dashboard silently one day stale. The scheduler had no dependency concept — jobs were independent crontab lines whose correct ordering was an accident of their original authoring times, unenforced by anything.
- **Exhibit B — the WARNING that held for six days (#2085):** a nightly metrics job called the local relay and got HTTP 400 — a real failure, its input roster never refreshing. The error was caught and logged as `WARNING` in a log nobody tails. **Six days** of metrics computed on a stale roster; the log line's severity was the entire difference between a same-day fix and a week of quiet wrongness.
- **Exhibit C — the cron that never once succeeded:** a dashboard job needed ~3.6 GB on a droplet with 3.9 GB total; the OOM killer terminated it on **every single run since deployment**. It had never produced output — and its consumers had never noticed, because the previous output file just… stayed there, getting older, looking like data. (The job's real fix is a host migration, tracked; the *detection* fix shipped.)

## How it was detected

A: wrong-looking numbers one morning, traced to timestamps. B: eventually, a human asked why a metric hadn't moved in a week. C: the source-mining audit for this very repo found the OOM kill pattern in system logs — the job's own logging said nothing, because the OOM killer doesn't let you log your own death.

## Root cause

Three surfaces, one deep cause: **liveness and correctness were conflated everywhere.** A cron that runs isn't a cron that worked (A: ran at the wrong time; C: ran and died). A log with no ERROR lines isn't a system with no errors (B: the error was there, dressed as a WARNING). Output that exists isn't output that's fresh (all three). Every monitoring surface answered "is it alive?" when the operative question was "is it right?"

## Blast radius

Weeks of stale morning dashboards; six days of wrong metrics; one job's entire service life as a zombie; and — the real cost — the audit obligation each discovery created: *what else is politely degraded right now?*

## The fix

- **Dependencies became explicit:** the scheduled-job registry gained ordering/depends-on metadata, and the chain's timing is verified against it — job B may not fire before job A's success marker exists.
- **Severity policy by consequence, not by exception type:** an error that means "tonight's output will be wrong" is an ERROR (and pages via the ops inbox), regardless of how recoverable the *code* found it. The 400-as-WARNING class was reclassified wholesale.
- **Freshness checks on outputs, not just exit codes on processes:** consumers assert input recency; a drift-detector suite audits the scheduled-job registry against reality — unregistered jobs, phantom registry entries, jobs whose outputs have stopped advancing. It currently emits *hundreds* of findings per sweep (197 unregistered-job flags in one recent window), which is what an honest backlog looks like after years of accretion.
- **OOM-class deaths surfaced:** system-level kill events joined the health scan, because dead processes don't file their own reports.

## Has the guard fired since?

Continuously — the drift detectors are the noisiest guards in the fleet by design (hundreds of registry findings per sweep, being burned down). The freshness assertions have caught two more stale-input incidents at consumption time, both same-day instead of week-scale.

## Lessons for agent-driven development

1. **"Runs" is not "works"; "exists" is not "fresh"; "no ERROR lines" is not "no errors."** Monitor correctness properties, or you're monitoring your own optimism.
2. **Severity belongs to consequences.** Classify log levels by what the failure does to output truth, not by how gracefully the code caught it.
3. **Cron lines are not a dependency graph.** Implicit ordering-by-schedule breaks silently; if B needs A, make the need mechanical.
4. **Some deaths leave no log — the killer writes the record.** Check the system's ledger (OOM, signals) for jobs that never got to say goodbye.
