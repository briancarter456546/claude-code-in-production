# Our deploy script reported success for months — the relay answered HTTP 200 and put the failure in the response body

**Keywords:** HTTP 200 with error body, transport status versus command status, remote exit code not propagated, deploy reported success wrote nothing, caching a failed response, silent deploy failure, checksum verification after deploy, agent deploy script exit 0, relay error swallowed, status code only error handling

**Incident date:** 2026-09-18 · **Internal refs:** #2812 · **Status:** open — the fix lives in an uncommitted scratch script; the response-caching path still collapses failure into success

---

## What broke

Every machine-to-machine action here goes through a local HTTP relay instead of direct SSH; that decision is [ADR-001](../adr/001-local-http-relay-instead-of-raw-ssh.md), and it fixed a real outage ([PM-002](002-concurrent-ai-agents-ssh-rate-limit-lockout.md)). A session asks the relay to run something on the always-on server, and reads the response.

A session building a web page wrote a small script to publish it: chunk the file, push the chunks through the relay, done. The script **exited 0.** The target directory on the server was **empty.** The failure — a refused connection on the transport leg — had been delivered inside the response body, under a 200.

The script caught transport exceptions, as scripts do. There was no exception. There was no error status. There was an error *string*, in a field nobody read.

Then the sentence that made this a postmortem rather than a bug. The operator, reading the finding: **"every page I've put on that site went through that script."**

## How it was detected

By a page that was not there. Not by the script, not by the relay's health endpoint, not by any log — the only signal was a human opening a URL and seeing nothing, then asking why a successful deploy had deployed nothing.

There was no way for the session to know. From inside the script, a failed publish and a successful publish are byte-identical: exit 0, no exception, a 200, and a body it did not parse.

## Root cause

**A status code describes the transport. It was being read as a description of the work.** Three layers of the relay each drop a piece of the truth, and the outcome is a success-shaped response for a failed operation.

**1. The remote exit code never crosses the boundary as a code.** One function runs the remote command. On a non-zero exit it returns the output *and* an error string assembled from the remote error output, or a rendering of the exit status if there was none. That string is the only place the remote failure exists. Past that function there is no integer, no field, nothing structured — so no caller downstream can branch on it without string-matching.

**2. The shared caching wrapper discards the error whenever there is any output.** Verified in the live source: it returns the output with the error field set to `None` if the output is not `None`, and **stores that output in the response cache.** A command that printed something to standard output and then failed is indistinguishable from one that succeeded — and its failed result is now cached and served to the next caller.

**3. The endpoints that use that wrapper therefore answer 200.** They cannot do otherwise; by the time they see the result the error is gone. The endpoints that call the runner directly *do* return a gateway error, which is why this looked inconsistent in the field and why the operator's first reading of the relay's behaviour was that it answers 200 for a refused connection — on the paths that go through the cache, the effect is exactly that.

The deeper cause is an interface boundary that lost a field. Once the remote exit status was collapsed into a string and then dropped, **no amount of careful error handling in any caller could recover it.** The API offered its consumers only the wrong question.

## Blast radius

**Unknown, and that is the finding.** Every page published through that script may or may not have landed; there is no record either way, because nothing ever compared what was sent with what arrived. Some pages are visibly present, which proves those succeeded. The rest cannot be distinguished from never-attempted.

Wider: **every script here that talks to the relay and checks only the status code has the same defect.** No audit of those call sites has been done. The canonical deploy path has not been checked.

This is the fourth distinct instance of the same family in this repository — [PM-028](028-the-push-that-lied.md) verified a push against a stale cached reference, [PM-032](032-exit-zero-wrong-answer.md) shipped contaminated results under a clean exit, and [PM-029](029-deploy-verified-then-reverted-thirty-minutes-later.md) verified a deploy that a scheduled job then reverted. In all four, **the verification step existed and measured the wrong thing.**

## The fix

Honest status: **contained by nothing, and the repair is not in version control.**

The replacement script, which exists as a scratch file, does two things right and both are general:

- **Parse the body and treat a non-empty error field as a failed call**, retrying with backoff. The status code is not consulted for the success of the work.
- **Compare a digest computed on the server against the digest computed locally, and exit non-zero on mismatch.** This is the part that actually matters: it does not ask the transport whether the transport worked, it asks the destination what it now holds. **A checksum comparison is the only proof a deploy landed.**

What still needs doing, and is filed:

1. Audit every relay-consuming script, and the canonical deploy path, for status-code-only error handling.
2. Either give the relay real error statuses on the cached paths, or ship a committed, versioned client helper that parses the body — so that "call the relay correctly" is a library, not a discipline.
3. Stop caching failed responses. A cached failure is served as success to every later caller.

## Has the guard fired since?

**There is no guard.** Nothing prevents the next script from reading a status code and believing it, and the fix is a scratch file in a temporary directory. Recorded here in that state on purpose: the gap between "we know exactly what the bug is and how to fix it" and "the fix is in the repository and enforced" is where this class of defect lives, and calling it fixed at the point of diagnosis is how it recurs.

The one durable artifact so far is the rule, which is worth more than the script: **a deploy is not done until the destination has been asked what it holds.**

## Lessons for agent-driven development

1. **Transport status is not operation status.** HTTP 200 means the relay answered. It says nothing about whether the remote command ran, succeeded, or wrote a byte. Any API that proxies command execution must carry the remote exit status as a structured field, all the way out.
2. **Never drop an error because there was also output.** Failing commands print. Output and error are independent, and a conditional that prefers output over error converts every noisy failure into a success.
3. **Never cache a failed response.** It turns a transient failure into a lasting lie for every subsequent caller.
4. **Verify at the destination, not at the boundary.** Ask what is there — checksum, row count, rendered page — rather than asking the pipe whether the pipe worked. Every entry in this family failed by verifying the near end.
5. **If correct use of your API requires discipline, ship a client.** Telling every future script to parse the body means the next script will not. A versioned helper that exits non-zero is the only form this fix survives in.
6. **When an operator says "everything went through that script", believe the scope before you believe the samples.** The visible successes prove only themselves; the question is what the silent calls did.
