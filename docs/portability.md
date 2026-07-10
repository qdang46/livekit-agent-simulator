# Multi-repo portability

`livekit-agent-simulator` is **target-agnostic**. Each consumer repo owns a gitignored
`.agent-sim/` folder; the Python package never imports worker or dashboard code.

## What is generic (sim core)

| Layer | Behavior |
|-------|----------|
| **Dispatch** | Opaque JSON string → `RoomAgentDispatch.metadata`. Sim does not parse keys. |
| **Scenario** | `Execute`, `Dispatch`, `Persona`, `PassCriteria` — same JSONL for any agent. |
| **Transcripts** | `lk.transcription` (LiveKit standard) + configurable data payloads (`transcript_payload_types`, default `transcript_turn`). |
| **Dedupe** | Multiple sources (sim.gemini, lk.transcription, data topics) merged with source priority so turn count stays accurate. |
| **Tools** | Optional `observe.tool_event_patterns` — each project maps its own data-topic JSON. |

## Per-target setup (in `<repo>/.agent-sim/`)

1. **`config.yaml`** — LiveKit URL/key/secret, `agent_name`, `simulator.google_api_key`.
2. **Optional `livekit.dispatch_metadata`** — default opaque JSON for all runs.
3. **Optional per-scenario `Dispatch.metadata`** — overrides config default.
4. **`observe.data_topics`** — list topics your worker publishes (empty = record all).
5. **`observe.tool_event_patterns`** — only if you want `tool.start` / `tool.end` in the log.

## Example: voice-ai-worker + dashboard

Dashboard builds dispatch metadata via `buildWorkerDispatchMetadata(customAgentId, …)` in
`demo-retell-ai-dashboard/src/server/worker/dispatch-metadata.ts`.

Worker reads `customAgentId` from job metadata in `voice-ai-worker/src/bootstrap/job-metadata.ts`.

Worker publishes:

- `voice_ai.transcript` — `{ type: "transcript_turn", turn: { role, text } }` (`publish-flow-event.ts`)
- `voice_ai.flow` — flow runtime events (optional tool pattern mapping)

**Target-only** scenario line (not in sim package):

```json
{"kind":"Dispatch","spec":{"metadata":"{\"customAgentId\":\"agent_xxx\"}"}}
```

**Target-only** `config.yaml` snippet:

```yaml
observe:
  data_topics:
    - voice_ai.flow
    - voice_ai.transcript
  tool_event_patterns:
    - match: { topic: voice_ai.flow, type: tool_started }
      emit: tool.start
```

## Example: unknown / third-party LiveKit agent

Minimum config — no custom data topics:

```yaml
livekit:
  agent_name: "their-agent"
observe:
  lk_transcription: true
  data_topics: []
  tool_event_patterns: []
```

Scenario with `Execute.first_speaker: user` if the agent waits for caller audio.

If the worker uses a different transcript payload type, set:

```yaml
observe:
  transcript_payload_types:
    - "live_transcript"
```

## Verification checklist

```bash
lk-sim preflight --root /path/to/target
lk-sim validate smoke-hello --root /path/to/target
lk-sim execute smoke-hello --root /path/to/target
```

Expect `status: done`, judge `pass`, `turn_count` ≈ scenario `max_turns`, exit code 0 (UTF-8 JSON on Windows).
