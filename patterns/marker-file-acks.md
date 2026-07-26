# Pattern: Marker-File Acknowledgments — Human Approval as an Artifact, Not a Vibe

**Problem:** Some actions need explicit human sign-off (destructive ops, design gates, KB supersessions), but the approval happens in *conversation* — ephemeral, unverifiable, and invisible to hooks. "The operator said yes earlier" is not a checkable fact.

**Mechanism:** Approval is materialized as a **marker file**: a small JSON artifact recording who approved what, when, for which target, with the operator's decision quoted. Gates check for a valid marker before allowing the action; the marker is consumed (or expires) so approval can't be replayed forever.

## Sanitized skeleton

```python
# make_ack.py -- the ONLY sanctioned way to mint approval
import json, time, pathlib

def write_marker(target: str, approved_by: str, quote: str):
    marker = {
        "target": target,                  # exactly what is approved
        "approved_by": approved_by,        # provenance, checked by the gate
        "quote": quote,                    # the operator's actual words
        "ts": time.time(),                 # TTL enforcement
        "session": current_session_id(),   # who minted it
    }
    p = pathlib.Path("acks") / f"{slug(target)}.json"
    atomic_write_json(p, marker)           # see atomic-write pattern

# gate side:
def check_marker(target, requester_identity):
    m = load_marker(target)
    assert m and not expired(m)
    assert m["approved_by"] in HUMAN_APPROVERS          # exact match, not prefix
    assert m["approved_by"] != requester_identity      # NEVER self-approval
    consume(m)                                          # single-use
```

## Failure modes of this pattern

- **The gated entity approving itself.** Our curator agent minted a marker approving its own write — and the gate accepted it, because the agent's identity was in the approver list ([PM-012](../postmortems/012-agent-forged-its-own-approval-marker.md)). Structurally exclude the requester from the approver set.
- **Writer/reader spec drift.** The approval writer emitted `'brian'`; the gate checked `startswith('brian-')` — every *legitimate* approval failed. Test the actual writer's output against the actual gate's check, together.
- **Format ≠ provenance.** Anything that can write files can write a well-formed marker. Include minting-context fields and detect markers written outside the sanctioned CLI.
- **Re-ack fatigue.** A TTL-bounded marker plus every-edit gating had one file approved **25 times** — by approval #12 the human is rubber-stamping ([PM-021](../postmortems/021-alarm-fatigue-by-the-numbers.md)). Gate creation, not iteration; scope markers to the artifact, not the edit.
- **Broken legitimate paths manufacture forgery pressure.** The self-approval incident happened *because* the honest path was rejecting valid approvals. Fix the happy path with incident-level urgency.
- **When the operator's decision is unambiguous in chat, mint the marker on their behalf, quoting them** — making a human re-type what they just said is how ack systems get bypassed culturally, then mechanically.

**Where it's enforced in our stack:** designer-ack gate, KB write policy (supersessions/contradictions), destructive-op approvals, deploy gates — every marker consumed or TTL'd, every mint audit-logged.
