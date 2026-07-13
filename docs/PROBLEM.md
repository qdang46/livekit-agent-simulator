# Known Problems & Research Items

## Gemini "answering" calls (SIP callee) on LiveKit Cloud

### Problem

Current `outbound_sip` flow: `call_to` = **agent's inbound DID** → agent joins room → audio bridge → Gemini converses.

But calling a **real PSTN number**:

```
lk-sim dial +84xxxxxxxxx  ──►  Cloud Trunk  ──►  PSTN  ──►  Real phone rings
                                                              │
                                                            Human picks up
                                                              │
                                                            Worker hears human,
                                                            Gemini hears nothing
```

Gemini can only "answer" when the call lands in a **room Gemini is in**. On Cloud:
- Agent has an inbound DID + dispatch rule → agent-room
- Gemini needs a **separate inbound DID + dispatch rule** → sim-room
- Currently no DID is provisioned to route into sim-room

### Potential solutions

| Approach | Description | Requires |
|---|---|---|
| **DID routing to sim-room** | Buy a number / DID + dispatch rule pointing to sim-room | LiveKit provisioning |
| **Self-host SIP + sip-to-ai** | LiveKit SIP docker local + in-process callee | Docker + vendored `sip-to-ai` Apache-2.0 code |
| **Twilio SIP trunk hairpin** | Twilio routing loops back into sim-room | Twilio config |

### Related references

- Plan: `docs/plans/PLAN-20260713-simleg-refactor.md` (T6 vendor sip-to-ai)
- Telephony docs: `docs/telephony.md`
- Cloned ref: `references/sip-to-ai/` (Apache-2.0 licensed SIP/RTP stack)
