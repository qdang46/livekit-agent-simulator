# WIP — gaps toward replacing a developer talking to the agent

Goal: **`lk-sim` replaces manual “open mic and chat with the voice agent”** for day-to-day QA — full-stack LiveKit room, black-box agent, forensic report + web replay.

Not the goal (different products): LiveKit **in-process** text unit tests inside agent code; 50k concurrent load platforms; full production observability SaaS.

---

## Research note (2026-07-12)

Sources: LiveKit Agents testing docs, Hamming metrics / persona templates, Coval / Cekura / Okareo / Future AGI / Phonely landscape; internal audit of `asserts.py`, `event_writer.py`, `caller-pattern-plan.md`.

### How the industry splits testing

| Layer | Who owns it | What it is |
|---|---|---|
| **In-process unit / session** | LiveKit Agents `AgentSession` + pytest/Vitest | Fake STT/LLM/TTS, `result.expect…`, LLM judge, metrics (EOU, TTFT, TTFB) — **no real WebRTC room** |
| **Black-box room / audio E2E** | Hamming, Coval, Cekura, Bluejay, Roark, **lk-sim** | Real (or near-real) room + audio pipeline + sim caller |
| **Load** | `lk perf agent-load-test`, Hamming concurrent | Many rooms / SIP load |
| **Prod observe** | OTel, Hamming/Coval/Cekura online eval | Drift, P90 latency, alerts |

LiveKit official stance: native tests for **agent logic**; for **full audio pipeline** they point to third-party tools. lk-sim sits in that E2E slot — **complement**, not replace, Agents pytest.

### Competitive snapshot (2026-07-12)

| Capability | lk-sim | Hamming | Coval | Cekura | Future AGI | LiveKit pytest |
|---|---|---|---|---|---|---|
| Real LiveKit room | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ (text session) |
| AI persona caller | ✅ Gemini Live | ✅ | ✅ | ✅ | ✅ | ❌ |
| Barge / silence / noise | ✅ Script + mixer | ✅ | ✅ | ✅ | partial | ❌ |
| Recovery assert (+ timing) | ✅ `Assert.outcomes.recovery` | ✅ | ✅ | ✅ | roadmap | ❌ |
| Forensic local log + web | ✅ strong | cloud | cloud | cloud | SDK | partial |
| MCP / coding-agent | ✅ **diff** | ❌ | partial | ❌ | ❌ | ❌ |
| CLI portable / self-host | ✅ MIT | closed | closed | closed | SDK+cloud | open framework |
| Latency metrics hard | ✅ Assert `latency` + `summary.metrics` | ✅ | ✅ | ✅ | roadmap | metrics helpers |
| pass@k | ✅ ``--repeat --pass-at-k`` | ✅ | ✅ | ✅ | ✅ | flaky patterns |
| Fail → golden | ✅ ``scenario-from-run`` | ✅ | ✅ | partial | partial | manual |
| Accent matrix | ❌ | ✅ | ✅ | partial | partial | ❌ |
| SIP / telephony | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Load test | ❌ | ✅ | partial | ✅ | cloud | ❌ |
| Prod observe | ❌ | ✅ | ✅ | ✅ | eval | OTel elsewhere |

**Niche:** open-source, local-first, forensic-first, MCP-native black-box LiveKit — dev/coding-agent loop, not Hamming/Coval SaaS.

### Metrics industry cares about

| Metric | Industry target (Hamming-ish) | lk-sim today |
|---|---|---|
| Turn-taking / TTFW | P90 e2e &lt; ~3.5s; first word often &lt;2.5s | ✅ `summary.metrics` (p50/p95/p99, TTFW, recovery, barge rate) + Assert type **`latency`** + suite columns |
| Barge-in recovery | Agent re-engages; recovery &gt;90% | ✅ Assert `recovery` + optional `max_ms_after_barge_to_agent_final` + `caller.behavior_summary` |
| Task completion | &gt;90% | Assert + PassCriteria judge |
| Flake / pass@k | Statistical eval | ✅ ``--repeat N --pass-at-k K`` |
| Fail → golden | Prod/sim failure → permanent test | ✅ ``scenario-from-run <run-id> [--write]`` |
| Suite CI gate | Non-zero exit, matrix | ✅ `execute-all` matrix + hard status/assert/script (judge soft unless `--strict-judge`) |

### Audio realism competitors sell

Accent / noise / mid-sentence barge-in **timing** / multi-voice — we have traits, mixer, cues catalog, vocal barge WAVs (en/vi), recovery timing assert. Still weak on **accent matrix**, SNR levels as first-class, DTMF, multi-voice packs, WER/audio-native eval.

---

## Already in good shape

| Capability | Notes |
|---|---|
| Black-box room + dispatch | Opaque metadata; any LiveKit agent |
| Gemini Live sim caller | Persona / Context / Execute |
| Caller character (Hamming-aligned) | `constraints`, `speech_conditions`, `Behavior` → Script compile |
| Traits library | impatient, interrupts, elderly, angry, backchannel, hangup_threat, code_switch, … |
| Scripted cues | `agent_speaking`, `gemini_text` / `room_pcm` |
| Cue catalog multi-repo | `builtin:…`, `.agent-sim/cues/`, `cues.aliases` / `dirs` |
| Parallel speech+noise | `ParallelMicMixer` |
| Barge-in (harder) | vocal PCM + blip, `interruption` by sim, recovery asserts |
| Silence / user hold | `silence_after_cue_ms`, dead_call guard while scripted silence |
| Forensic log | `events.jsonl`, timeline, summary, SQLite |
| Optional LLM judge | `PassCriteria` |
| Local stereo audio | `conversation.wav` (L=sim, R=agent) |
| Web replay + markers | barge / silence / recovery highlight |
| Batch + compare | `execute-all` suite matrix, `compare` (thin — no golden baseline) |
| Scaffold / guide | `scenario-init`, `guide`, `install.sh`, `lk-sim cues` |
| CLI ↔ MCP parity | Single `ops` surface |

P0 “talk like a person on one call” ≈ **done for v1**.

---

## P0 — “Talk more like a real person” (closed for v1)

| Gap | Status | Notes |
|---|---|---|
| Diverse personas | **Done (v1)** | `Persona.traits[]` + constraints |
| Parallel speech+noise | **Done** | Mixer |
| Interruption / barge-in | **Done (v1)** | Still polish: wider vocal WAV library |
| Silence / user gone | **Done** | 20s hold + dead_call guard |
| Outcome / tool / recovery asserts | **Done** | including optional recovery timing |
| Multi-repo cues | **Done** | builtin + target override |
| Caller pattern redesign | **Done (v1)** | `docs/caller-pattern-plan.md` |

**P0 residual polish (optional, not blockers):**

- Broader Vietnamese / EN **speech** WAV pack (variants of wait / sorry / backchannel)
- Optional `barge_in.auto_blip: false` when using vocal PCM (partially via voice-asset detection)
- `noise_gain` / SNR levels as first-class `speech_conditions`

---

## P1 — Daily QA / regression loop ← **do next**

Aligned with LiveKit/Hamming “regression + offline eval” without becoming SaaS.

| Priority | Gap | Why (from research) | Candidate work | Status |
|---|---|---|---|---|
| **P1.1** | Suite report + CI gate | Automated regression is table stakes | `execute-all` → suite matrix + `suite-*.json/md` | **Done (v1)** |
| **P1.5** | Exit-code policy | CI needs hard gates | hard: status/assert/script; judge soft unless `--strict-judge` | **Done (v1)** |
| **P1.3** | **Voice metrics hard** | Latency is what humans “feel”; competitors gate on P95/TTFW | `summary.metrics` + Assert type `latency` + suite columns (p50/p95/ttfw) | **Done (v1)** |
| **P1.2** | **Flake control (pass@k)** | Gemini caller is stochastic | `execute --repeat N --pass-at-k K` + suite column + MCP | **Done (v1)** |
| **P1.4** | **Fail → golden** | Hamming/Coval flywheel: fail becomes permanent case | `lk-sim scenario-from-run <run-id>` draft JSONL from transcript + script markers | **Done (v1)** |
| **P1.7** | **Hard hangup** | `hangup_threat` is prompt-only; real callers hang up | Script/Behavior `hang_up` + Assert ended_by | **Done (v1)** |
| **P1.6** | Text-fast mode | Cheap loop before full voice | Optional text path (later if suite cost hurts) | Deferred |

### Suggested ROI order

```text
1. ~~P1.3 metrics pack + latency Assert + suite columns~~ Done v1
2. ~~P1.2  --repeat / pass@k~~ Done v1
3. ~~P1.4  scenario-from-run~~ Done v1
4. ~~P1.7  hang_up action + end-call assert~~ Done v1
5. P0 polish  vocal pack + noise_gain  ← next
```

---

## P2 — Scale / production-adjacent (defer)

| Gap | Notes | Competitors |
|---|---|---|
| Accent matrix | Multi-locale / multi-voice packs; stay trait + locale for now | Hamming, Coval |
| Concurrent / load rooms | Use `lk perf`; no Gemini N-way | Hamming, Cekura |
| SIP / telephony | Real phone numbers; DTMF/IVR | Cekura, Hamming, Coval |
| Prod import / shadow replay | Online eval SaaS territory | Hamming Observe, Coval |
| Auto-gen scenarios from SOP | Nice-to-have | Future AGI, Phonely |
| Multi-party handoff | LiveKit multi-agent workflows | — |
| Audio-native eval (WER, prosody) | Transcript + judge only today | Okareo, Hamming |
| OTel export from lk-sim | Optional bridge to agent observability | — |

---

## Developer manual work vs lk-sim

| Manual developer | lk-sim today |
|---|---|
| Open mic, greet agent | ✅ |
| Happy-path flow | ✅ |
| Barge-in, silence, noise | ✅ (PCM + vocal cues) |
| Switch language / voice | ⚠️ config — no scenario matrix |
| Check tool calls | ✅ Assert.tools |
| Check interruption recovery | ✅ Assert recovery (+ timing) |
| Re-listen | ✅ wav + web |
| Fail CI on slow turns | ✅ Assert `latency` (hard via assert_verify) |
| Compare before/after | ⚠️ compare — no golden baseline |
| Stable pass under flake | ✅ `--repeat N --pass-at-k K` (hard via assert_verify) |
| Promote bug to regression | ✅ `scenario-from-run <run-id> [--write]` (draft then review) |
| Sim caller hard hangup | ✅ Script `hang_up` action + Assert `ended_by` |
| Run 20 cases before ship | ✅ execute-all suite matrix + hard gate (judge soft) |
| Stable pass under flake | ✅ `--repeat N --pass-at-k K` (hard via assert_verify) |
| Promote bug to regression | ✅ `scenario-from-run <run-id> [--write]` (draft then review) |
| Call real SIP | ❌ |
| Load 100 concurrent | ❌ |

---

## Suggested order (post-research)

1. ~~Behavioral richness (P0)~~ **Done v1**
2. ~~Hard asserts + recovery~~ **Done**
3. ~~**P1.1 + P1.5** — suite matrix + CI exit policy~~ **Done v1**
4. ~~**Caller pattern redesign (Hamming-aligned)**~~ **Done v1** — `docs/caller-pattern-plan.md`
5. ~~**P1.3** — metrics hard~~ **Done v1** (`metrics.py`, Assert `latency`, suite columns)
6. ~~**P1.2** — pass@k~~ **Done v1** (``execute --repeat --pass-at-k``, MCP, CLI)
7. ~~**P1.4** — scenario-from-run~~ **Done v1** (``scenario-from-run <run-id>``, MCP, draft JSONL)
8. ~~**P1.7** — hard hangup~~ **Done v1** (Script action hang_up + Assert ended_by + CLI/MCP)
9. Later: SIP; load via `lk perf` (not Gemini N-way); accent packs if needed

Keep portable: no consumer keys in `src/`; extend via scenario / `.agent-sim/cues` / config / verify plugins (`AGENTS.md`).

---

## Explicit non-goals (for now)

- Replacing LiveKit **in-process** Agents pytest / FakeActions session tests
- Full Hamming/Coval-class production monitoring SaaS
- 50k concurrent simulation
- Built-in neural accent models
- Domain hardcoding one monorepo’s business into core

---

## Status

| Area | Status |
|---|---|
| Core sim + report + web replay | Done |
| P0 behavior + structured pass + cue catalog | **Done (v1)** |
| Caller character (constraints / Behavior / recovery) | **Done (v1)** |
| P1.1 suite + P1.5 exit gate | **Done (v1)** |
| P1.3 latency metrics hard | **Done (v1)** |
| P1.2 pass@k | **Done (v1)** |
| P1.4 fail → golden | **Done (v1)** |
| P1.7 hard hangup | **Done (v1)** |
| P2 load / SIP / accent / prod observe | Deferred |

Update this file when gaps close or priorities change.
