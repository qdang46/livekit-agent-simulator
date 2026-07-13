# Plan Report — SimLeg telephony (unified inbound / WebRTC / outbound)

## Summary (read this first)

- **You asked:** Research kỹ (Exa + sub-agents) và tạo plan cho telephony — **Gemini luôn thay người**, log/assert/replay giữ như hiện tại; inbound / WebRTC / outbound dùng **chung design pattern**.
- **What is going on:** Hôm nay lk-sim chỉ có `WebRtcSimLeg` ngầm (`connect_simulator` + `GeminiCallerBridge`). SIP outbound/inbound cần cùng pipeline 7 phase nhưng **đổi transport leg** — không fork Observer/converse/judge.
- **We recommend:** **Template Method + Strategy** — `SimLeg` protocol; `Caller.mode` trong scenario; **vendor `sip-to-ai` SIP/RTP** vào `sip_callee/` (Apache-2.0); **một** `GeminiCallerBridge`; T0→T1→T2 outbound → inbound → asserts.
- **Risk:** **High** on T2 (vendor + wire PCM). **Low** on T0/T1. CI trunk defer; local manual dev.
- **Status:** Waiting for your OK — reply **go ahead** to implement

## Feature planning

### Recommended approach (one paragraph)

Giữ `run_orchestrator` làm **template method** (7 phase). Tách Phase 3 thành `SimLeg.connect()` — factory từ `scenario.effective_caller_mode()`. **SimBrain** (`GeminiCallerBridge`, `ScriptRunner`, `ParallelMicMixer`) và **ObserveReport** (`Observer`, `EventWriter`, `LocalConversationRecorder`) **không nhân bản** theo mode. Chỉ thay:

1. Cách **Gemini audio** tới agent (WebRTC mic publish vs SIP RTP bridge)
2. Cách **agent audio** tới Gemini (vẫn subscribe agent WebRTC track trong room — verified)
3. Thứ tự telephony (outbound: `prepare_ms` → `CreateSIPParticipant`)

**Product rule:** Gemini = simulated human trên mọi topology. Không ship observe-only PSTN.

### Three topologies — same stack

| `Caller.mode` | Gemini role | Harness action | Agent hears sim via |
|---|---|---|---|
| `webrtc_sim` (default) | Caller | Join WebRTC `lk-sim-caller` | WebRTC audio track |
| `outbound_sip` | Callee (nhấc máy) | `lkapi.sip.create_sip_participant` sau agent join | SIP participant in room |
| `inbound_sip` | Caller (gọi PSTN) | Originate call tới `Telephony.dial_in` (outbound trunk → inbound DID) | SIP participant in room |

**Shared unchanged:** Persona, Script, Behavior, Execute, Assert, PassCriteria judge, `events.jsonl`, `summary.json`, `conversation.wav`, suite gate, `--repeat` / `pass@k`.

### Design pattern diagram

```text
RunOrchestrator
  ├─ RoomLifecycle     LiveKitAdapter.create_room_and_dispatch + wait_for_agent
  ├─ SimLeg.connect    Strategy: WebRtc | OutboundSip | InboundSip
  ├─ SimBrain          GeminiCallerBridge + ScriptRunner (+ nudge)
  ├─ Converse          _conversation_loop (unchanged)
  ├─ ObserveReport     Observer + EventWriter + recorder
  └─ VerifyJudge       asserts + script_verify + judge
```

### Prior art (GitHub / industry)

| Source | What we reuse | What we avoid |
|---|---|---|
| [livekit/sip `lktest-sip-outbound`](https://github.com/livekit/sip/tree/main/test/lktest-sip-outbound) | Loopback SIP E2E without PSTN; attr/audio checks | Copying Go test into Python core |
| [LiveKit make_call recipe](https://docs.livekit.io/reference/recipes/make_call/) | `dispatch` → `create_sip_participant` | Dial-before-agent (bad for sim) |
| [outbound-caller-python](https://github.com/livekit-examples/outbound-caller-python) | `session.start` before dial; `wait_until_answered`; `SipCallError` | Pattern B as **default** (not black-box) |
| [voice-ai-worker `scripts/outbound.ts`](C:\Users\ADMIN\Documents\Projects\voice-ai-worker\scripts\outbound.ts) | `prepare_ms` after dispatch | Verbatim port; parsing `customAgentId` in core |
| [sip-to-ai](https://github.com/aicc2025/sip-to-ai) | **Vendor** `sip_async/` + codec utils (Apache-2.0) | `app/ai/*` multi-provider; `main.py` |
| [livetok/sip-proxy](https://github.com/livetok-ai/sip-proxy) | **Pattern only:** per-call callback Persona (v2) | Copy Go code; Twilio branches |
| [sip2ai](https://github.com/dmitry-sinina/sip2ai) / [didww-voice-agent](https://github.com/edwinux/didww-voice-agent) | Reference RTP↔Gemini patterns | Full drachtio stack |
| [Hamming](https://hamming.ai/) | `call_path` separated from sim brain; forensic replay | Closed SaaS features (50k load, accent matrix) |
| [Coval outbound](https://docs.coval.dev/guides/outbound-voice) | Trigger → agent dials → sim answers (inverted inbound) | PSTN correlation webhooks in v1 |
| [Bluejay telephony](https://docs.getbluejay.ai/simulation-integrations/telephony) | Outbound = sim calls agent; Inbound = agent calls sim number | Cloud-only execution model |
| [Sipfront AI voicebots](https://sipfront.com/blog/2025/08/sipfront-launches-ai-voicebots-for-testing/) | Bidirectional SIP + realtime AI on RTP path | Commercial product scope |

### Integration points (verified in repo)

| File | Role in plan |
|---|---|
| `src/livekit_agent_simulator/run_orchestrator.py:54–215` | Phase 3 seam: replace `connect_simulator` + `room.disconnect` with `SimLegHandle` |
| `src/livekit_agent_simulator/livekit/adapter.py:57–135` | Keep dispatch/wait; move connect to `WebRtcSimLeg`; add `create_sip_participant` |
| `src/livekit_agent_simulator/gemini/live_session.py:80–118` | `watch_agent_tracks` unchanged; `publish_mic` → pluggable `SimAudioSink` |
| `src/livekit_agent_simulator/livekit/observer.py:76–91` | Pass SIP `sim_identity`; role assignment unchanged |
| `src/livekit_agent_simulator/scenario.py:28–39,94–109` | Add `Caller`/`Telephony` kinds + merge helpers |
| `src/livekit_agent_simulator/config.py:139–274` | Optional `telephony:` section + snapshot redaction |

### Sub-agents used

Yes — 4 parallel read-only agents:

1. LiveKit SDK / SIP API patterns ([agent](b51c8c45-3cac-406c-823a-b4d634768f2f))
2. Codebase integration map ([agent](b8318e2d-4184-414c-beb8-f2dc71871eda))
3. GitHub prior art ([agent](39285ab7-2831-4227-b006-97b352c49029))
4. Tests / risk / rollout ([agent](dc6e02ec-788b-4513-9da2-5b7f3e71945f))

Plus Exa: LiveKit outbound/testing docs, Hamming/Coval/Bluejay/Sipfront telephony QA, `sip2ai` / outbound-caller examples.

### Option B (deferred)

**`agent_dials` (Pattern B):** lk-sim chỉ dispatch + observe; worker gọi `create_sip_participant` trong entrypoint. Ship as **T5** — cần target agent hợp tác, không black-box. Không thay Pattern A làm default.

### Open questions (owner)

1. **Callee endpoint (resolved):** Vendor `sip-to-ai` `sip_async/` in-process; `call_to` = số/SIP terminate tới lk-sim SIP listener (local trunk / Twilio forward / inline trunk)
2. ~~**CI trunk:**~~ **Resolved — defer.** Dev phase = **local manual only**; PR CI stays unit/mock (`pytest -q`). Telephony E2E khi dev: `lk-sim execute` trên máy local với trunk trong `.agent-sim/config.yaml`. CI trunk/nightly **không cần** cho giai đoạn hiện tại.
3. **`wait_until_answered` default:** `true` (strict) vs `false` (match `outbound.ts`)?
4. **Inline trunk in v1:** Chỉ `sip_trunk_id` trước, hay cần inline `SIPOutboundConfig` ngay?
5. **Reference target:** `voice-ai-worker` `.agent-sim/` làm telephony suite mẫu?

## Evidence

1. **LiveKit docs:** [Outbound calls](https://docs.livekit.io/telephony/making-calls/outbound-calls/) — `CreateSIPParticipant`, inline vs stored trunk, `wait_until_answered`, agent must be dispatched separately when harness dials. [Testing](https://docs.livekit.io/telephony/testing/) — verify `kind=SIP`, `sip.callStatus`. [SIP participant](https://docs.livekit.io/reference/telephony/sip-participant/) — attrs `dialing|ringing|active|hangup`.
2. **Python SDK (verified upstream):** `LiveKitAPI.sip.create_sip_participant` — no separate `SipClient`; `SipCallError` with `sip_status_code` — [sip_service.py](https://github.com/livekit/python-sdks/blob/main/livekit-api/livekit/api/sip_service.py). Locked in repo: `livekit-api 1.1.1` (`uv.lock`).
3. **Our code:** `adapter.connect_simulator` (`adapter.py:127–135`) — WebRTC only today. `run_orchestrator` Phase 3 (`run_orchestrator.py:139–168`) — hard-coded `SIM_IDENTITY`.
4. **Reference harness:** `outbound.ts` — room create → dispatch metadata → `prepare_ms` → `createSipParticipant(..., waitUntilAnswered: false)`.

## T2 spike — SIP ↔ Gemini bridge (critical path)

**Problem:** Agent outbound nghe **SIP participant**, không nghe WebRTC `lk-sim-caller`. Gemini hôm nay publish WebRTC mic — **không tự động** lên nhánh PSTN.

### Deep research — vendor strategy (2026-07-13, updated)

**Kết luận (owner):** **Vendor copy có kiểm soát** từ [sip-to-ai](https://github.com/aicc2025/sip-to-ai) vào lk-sim — **không** chạy sidecar lâu dài; **không** copy Go từ [livetok/sip-proxy](https://github.com/livetok-ai/sip-proxy).

**Product rule giữ nguyên:** **một Gemini brain** (`GeminiCallerBridge` + scenario Persona) — nhiều transport leg (WebRTC / SIP). SIP layer chỉ lo RTP/G.711; không duplicate AI clients.

```text
LiveKit CreateSIPParticipant(call_to)
        ↓
sip_callee/ (vendored sip_async) nhận INVITE in-process
        ↓
audio_adapter: RTP G.711 ↔ PCM16 @ 8kHz
        ↓
GeminiCallerBridge (persona từ scenario)
        ↓
Observer + events.jsonl (như WebRTC)
```

**Provider-agnostic:** lk-sim core chỉ biết LiveKit `sip_trunk_id` / inline trunk — Twilio, Telnyx, Plivo, Asterisk, direct SIP đều qua trunk config; **không** branch provider trong `src/`.

| Repo | License | Verdict |
|---|---|---|
| **sip-to-ai** | Apache-2.0 | **Vendor SIP/RTP vào lk-sim** |
| **livetok/sip-proxy** | Không có LICENSE trên GitHub | **0 file copy** — chỉ học pattern |

---

### Vendor copy matrix — `sip-to-ai`

**Target path:** `src/livekit_agent_simulator/sip_callee/` + `THIRD_PARTY_NOTICES.md` (Apache-2.0 attribution).

#### ✅ Copy nguyên (core telephony)

| Source (sip-to-ai) | Dest (lk-sim) |
|---|---|
| `app/sip_async/__init__.py` | `sip_callee/sip_async/__init__.py` |
| `app/sip_async/async_sip_server.py` | same |
| `app/sip_async/async_call.py` | same |
| `app/sip_async/sip_protocol.py` | same |
| `app/sip_async/sdp.py` | same |
| `app/sip_async/rtp_session.py` | same |
| `app/sip_async/audio_bridge.py` | same |
| `app/utils/codec.py` | `sip_callee/codec.py` |
| `app/utils/ring_buffer.py` | `sip_callee/ring_buffer.py` |
| `app/utils/constants.py` | `sip_callee/constants.py` |
| `LICENSE` | `THIRD_PARTY_NOTICES.md` (sip-to-ai section) |

#### ⚠️ Copy rồi adapt (không dùng nguyên)

| Source | Lấy gì | Adapt |
|---|---|---|
| `app/bridge/audio_adapter.py` | 320-byte PCM frames, uplink/downlink queues | Rename → `sip_callee/pcm_adapter.py`; interface `SipAudioSink` |
| `app/bridge/call_session.py` | per-call task lifecycle | Rewrite → `sip_callee/call_session.py`; **bỏ** embedded AI client; wire `GeminiCallerBridge` |
| `app/ai/duplex_base.py` | duplex pattern (optional) | Tham khảo cho `SipAudioSink` protocol only |

#### ❌ Không copy

```text
app/ai/gemini_live.py          → lk-sim gemini/live_session.py
app/ai/openai_realtime.py
app/ai/deepgram_agent.py
app/ai/grok_voice.py
app/ai/sixtydb_tts.py
app/main.py                    → run_orchestrator + optional lk-sim callee-bridge
app/config.py                  → lk-sim config/scenario
agent_prompt.yaml              → scenario Persona
scripts/, examples/, docs/
```

#### ✅ Tests port (đổi import path)

| Source test | Dest |
|---|---|
| `tests/test_codec.py` | `tests/sip_callee/test_codec.py` |
| `tests/test_ring_buffer.py` | `tests/sip_callee/test_ring_buffer.py` |
| `tests/test_rtp_media_path.py` | `tests/sip_callee/test_rtp_media_path.py` |
| `tests/test_audio_bridge_paths.py` | `tests/sip_callee/test_audio_bridge_paths.py` (sau wire Gemini) |

**Không port:** `test_gemini_live.py`, `test_openai_*`, `test_grok_*`, `test_deepgram_*`.

---

### Vendor copy matrix — `livetok/sip-proxy` (pattern only)

**Không copy file Go.** Implement lại trong Python khi cần:

| sip-proxy file | Học gì | lk-sim implement |
|---|---|---|
| `README` callback API | per-call `system_instructions`, `voice`, `language` | **v2:** ephemeral HTTP callback; lk-sim push `scenario.persona_system_prompt()` khi SIP call start |
| `bridge.go` | SIP ↔ AI media bridge | `sip_callee/sip_async/audio_bridge.py` (từ sip-to-ai) |
| `rtp.go` | 20ms packetization | `rtp_session.py` (từ sip-to-ai) |
| `gemini.go` | 8k↔16k↔24k resample | `codec.py` + `GeminiCallerBridge` |
| `twilio.go` | Twilio TwiML webhook | **Không** — provider-agnostic via LiveKit trunk |
| `sip.go` | SIP state machine | `sip_async/` (từ sip-to-ai) |

---

### Target tree sau vendor

```text
src/livekit_agent_simulator/
  sip_callee/                    # vendored sip-to-ai (Apache-2.0)
    sip_async/                   # COPY
    codec.py, ring_buffer.py, constants.py
    pcm_adapter.py               # ADAPT từ bridge/audio_adapter.py
    call_session.py              # ADAPT — no AI client inside
    leg_server.py                # NEW — start/stop in-process SIP listener
  gemini/live_session.py         # GIỮ — single brain
  livekit/
    sim_leg.py
    outbound_sip_leg.py          # dial + wire sip_callee ↔ bridge
  THIRD_PARTY_NOTICES.md
```

---

### Persona sync

| Mức | Cách |
|---|---|
| **v1 (T2)** | Persona từ scenario → `GeminiCallerBridge` (cùng WebRTC path) |
| **v2** | Pattern từ livetok `callback-url`: per-call HTTP nếu cần isolate SIP process (unlikely if in-process) |

#### Không làm

- Copy nguyên `sip-to-ai` multi-AI (`openai`, `deepgram`, `grok`) — vi phạm AGENTS.md portable core
- Copy Go `sip-proxy` vào repo Python
- Observe-only dial mobile người thật
- Hairpin 2 room thay cho in-process callee
- Duplicate `gemini_live.py` từ sip-to-ai song song `GeminiCallerBridge`

**Spike acceptance (T2):**

- One end-to-end call: agent speaks ↔ Gemini persona audible on SIP leg
- `events.jsonl` shows `outbound.dial_answered` + alternating `transcript.*`
- Document chosen approach in `docs/telephony.md`

**Codec note:** SIP default G.711 @ 8 kHz; Gemini bridge uses 16 kHz PCM — resample at bridge ([codecs doc](https://docs.livekit.io/reference/telephony/codecs-negotiation/)).

## Steps (implementation checklist)

### T0 — Extract `WebRtcSimLeg` (refactor only)

- [ ] Add `src/livekit_agent_simulator/livekit/sim_leg.py` — protocol + `WebRtcSimLeg`
- [ ] Move `connect_simulator` usage from orchestrator into leg
- [ ] `pytest -q` green; smoke scenarios unchanged

**Acceptance:** Zero behavior change; `sim.connected` identity still `lk-sim-caller`.

### T1 — Contract + factory + docs

- [ ] Parse `Caller` / `Telephony` in `scenario.py` + `scenario_from_dict.py`
- [ ] `effective_caller_mode()`, `effective_telephony(cfg)`
- [ ] `sim_leg_factory(mode)` — SIP modes raise clear "not implemented" until T2/T3
- [ ] `TelephonyConfig` in `config.py` (optional `telephony:` block)
- [ ] `docs/telephony.md` — topology table, config/scenario examples, preflight checklist
- [ ] Unit tests: parse, merge, factory, backward compat (no `Caller` line)

**Acceptance:** Invalid mode / missing `call_to` fails at parse; WebRTC identical to T0.

### T2 — Outbound SIP (`outbound_sip`) + vendor sip-to-ai

- [ ] Vendor copy per matrix above → `sip_callee/` + `THIRD_PARTY_NOTICES.md`
- [ ] Port tests: `test_codec`, `test_ring_buffer`, `test_rtp_media_path`
- [ ] `sip_callee/leg_server.py` — in-process listener (`telephony.callee_listen_host/port` or auto ephemeral port)
- [ ] `SimAudioSink` / `pcm_adapter.py` — RTP PCM ↔ `GeminiCallerBridge` (not WebRTC `publish_mic`)
- [ ] `LiveKitAdapter.create_sip_participant()` wrapping `lkapi.sip.create_sip_participant`
- [ ] `OutboundSipSimLeg`: start leg_server → agent join → `prepare_ms` → dial `call_to` → wait active
- [ ] Events: `outbound.dial_started`, `outbound.dial_answered`, `outbound.dial_failed`, `sip.participant_connected`
- [ ] Observer `sim_identity` = SIP participant identity
- [ ] Template `templates/outbound-customer-sim.jsonl`
- [ ] `docs/telephony.md` — trunk setup (any provider), local dev flow

**Acceptance:** Full persona via `GeminiCallerBridge` on SIP leg; WAV L=sim R=agent; asserts pass.

**Local dev:** trunk trong `.agent-sim/config.yaml`; `call_to` trỏ endpoint nhận dial (có thể localhost hairpin qua Twilio/LK inline trunk). CI trunk defer.

### T3 — Inbound SIP (`inbound_sip`)

- [ ] `InboundSipSimLeg`: originate to `Telephony.dial_in` (outbound trunk → inbound DID)
- [ ] Gemini as PSTN caller; `first_speaker: user` default
- [ ] Inbound events; same bridge reuse from T2
- [ ] Document owner setup: inbound trunk + dispatch rule

**Acceptance:** Inbound scenario completes with same forensic artifacts as WebRTC.

### T4 — SIP asserts + suite

- [ ] Assert kinds: `sip_call_status`, `sip_participant_present`
- [ ] `summary.json` / suite columns: mode, dial_ms, sip_status
- [ ] Fixture-based unit tests (no trunk)

### T5 — Pattern B `agent_dials` (optional)

- [ ] `Caller.mode: agent_dials` — dispatch only, wait for SIP participant event
- [ ] Doc example; opaque `Dispatch.metadata` only

## Scenario / config contract

**`config.yaml`** (shared — no mode):

```yaml
livekit: { url, api_key, api_secret, agent_name }
simulator: { google_api_key, ... }
telephony:                    # optional defaults
  sip_trunk_id: ST_xxxx
  prepare_ms: 3000
  wait_until_answered: true
  krisp_enabled: false
```

**Outbound scenario:**

```jsonl
{"kind":"Scenario","spec":{"id":"outbound-customer-sim","tags":["telephony","outbound"]}}
{"kind":"Caller","spec":{"mode":"outbound_sip"}}
{"kind":"Persona","spec":{"name":"Skeptical callee","brief":"You answered a sales call. Be brief."}}
{"kind":"Telephony","spec":{"call_to":"+1..."}}
{"kind":"Execute","spec":{"timeout_s":120,"first_speaker":"user","max_turns":10}}
```

**Inbound scenario:**

```jsonl
{"kind":"Caller","spec":{"mode":"inbound_sip"}}
{"kind":"Telephony","spec":{"dial_in":"+1..."}}
{"kind":"Persona","spec":{"name":"Billing caller"}}
{"kind":"Execute","spec":{"first_speaker":"user"}}
```

**Merge rules:**

```text
effective_mode       = Caller.mode ?? "webrtc_sim"
effective_call_to    = Telephony.call_to   (required if outbound_sip)
effective_dial_in    = Telephony.dial_in   (required if inbound_sip)
effective_trunk        = Telephony.sip_trunk_id ?? config.telephony.sip_trunk_id
effective_prepare_ms = Telephony.prepare_ms ?? config.telephony.prepare_ms
```

## Files to touch

| File | Change |
|---|---|
| `src/livekit_agent_simulator/livekit/sim_leg.py` | **New** — protocol, WebRtc/Outbound/Inbound legs |
| `src/livekit_agent_simulator/livekit/adapter.py` | SIP API methods |
| `src/livekit_agent_simulator/run_orchestrator.py` | Phase 3 via factory |
| `src/livekit_agent_simulator/scenario.py` | Caller/Telephony kinds |
| `src/livekit_agent_simulator/scenario_from_dict.py` | Same |
| `src/livekit_agent_simulator/config.py` | `TelephonyConfig` |
| `src/livekit_agent_simulator/gemini/live_session.py` | `SimAudioSink` hook — SIP PCM in/out |
| `src/livekit_agent_simulator/sip_callee/**` | **New** — vendored sip-to-ai SIP/RTP (Apache-2.0) |
| `THIRD_PARTY_NOTICES.md` | **New** — sip-to-ai attribution |
| `tests/sip_callee/test_*.py` | **New** — ported codec/rtp tests |
| `src/livekit_agent_simulator/preflight.py` | Telephony checks when SIP scenario |
| `src/livekit_agent_simulator/asserts.py` | SIP assert kinds (T4) |
| `docs/telephony.md` | **New** |
| `templates/outbound-customer-sim.jsonl` | **New** |
| `tests/test_sim_leg*.py`, `tests/test_scenario_caller_telephony.py` | **New** |
| `WIP.md` | Mark implementation in progress when started |

## CI / test strategy

**Owner decision (dev phase):** Không cần CI trunk. Test telephony chạy **local manual** khi dev; CI PR chỉ unit/mock.

| Tier | When | What | Trunk? |
|---|---|---|---|
| **PR (required)** | Now | Unit: scenario parse, factory, config, mocked SIP API, assert fixtures | No |
| **Local manual** | Dev | `lk-sim preflight` + `lk-sim execute <scenario>` với trunk trong target `.agent-sim/config.yaml` | Yes (your dev trunk) |
| **CI telephony E2E** | **Defer** | Nightly/shared trunk — revisit khi telephony ổn định | Later |

Extend `tests/test_dispatch_mock.py` pattern for `create_sip_participant` mocks.

Mark integration: `@pytest.mark.telephony` — skip in `pytest -q` unless local `--run-telephony` or config fixture has `sip_trunk_id`.

## Risk matrix

| Risk | Level | Mitigation |
|---|---|---|
| SIP↔Gemini bridge | **High** | Vendor sip-to-ai `sip_async/`; single `GeminiCallerBridge`; port codec tests first |
| PSTN cost / wrong number | **High** | Allowlist doc; dedicated test trunk; hairpin for CI |
| Agent join vs dial race | Med | `prepare_ms` default 3000; dial only after `dispatch.agent_joined` |
| WebRTC regression | Med | T0 zero behavior change; default `webrtc_sim` |
| Opaque metadata parsing | **High** if done | Forbidden — `Telephony.*` only for dial params |
| `sip.callStatus` empty on SDK | Med | Prefer `wait_until_answered=True`; poll fallback |

## Anti-patterns

- Put `mode` in shared `config.yaml`
- Observe-only outbound without Gemini
- Duplicate converse/observe per mode
- Hardcode `customAgentId` / dashboard env in `src/`
- Port `outbound.ts` verbatim into core

## If you want more detail

### Recommended harness sequence (outbound Pattern A)

```text
create_room → [room_prepare_ms] → create_dispatch → wait_agent
→ connect_observer (WebRTC, auto_subscribe)
→ [telephony.prepare_ms]
→ create_sip_participant(wait_until_answered=True)
→ wire Gemini ↔ SIP via chosen bridge
→ converse until end condition
```

### Inbound note (verified)

LiveKit has **no** RPC to inject inbound SIP without real INVITE. `inbound_sip` mode = harness originates call to `dial_in` via outbound trunk (same as Coval trigger inversion), or external softphone — not a separate "simulate inbound" API.

### Competitive positioning

lk-sim niche unchanged: **open, local-first, forensic, MCP-native**. Telephony closes gap vs Hamming/Coval on `call_path` while keeping portable scenario JSONL + self-host reports.

---

**Next step:** Reply **go ahead** to implement **T0 + T1** first. T2 spike dùng **trunk local** trong `.agent-sim/config.yaml` — không block bởi CI.
