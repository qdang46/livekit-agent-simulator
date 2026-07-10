# Smoke test — first end-to-end run

Goal: prove the whole chain works against your local worker:
room create → agent dispatch → agent joins → sim caller joins → Gemini talks →
transcripts + events logged → report written.

## Prerequisites

1. Your LiveKit worker is **running** and registered with an explicit `agent_name`
   (e.g. `voice-ai-worker-local`). For voice-ai-worker: `pnpm dev` in that repo.
2. LiveKit Cloud (or self-hosted) URL + API key/secret.
3. A Google API key with access to `gemini-3.1-flash-live-preview` (same key works
   for the `gemini-2.5-flash` judge).

## Steps

All commands run from the repo you want to test (`--root` defaults to CWD):

```powershell
# 1. Scaffold .agent-sim/ (gitignored automatically)
uv run --directory C:\Users\ADMIN\Documents\Projects\livekit-agent-simulator lk-sim init

# 2. Fill in credentials
#    .agent-sim/config.yaml → livekit.url / api_key / api_secret / agent_name
#                             simulator.google_api_key

# 3. Verify connectivity BEFORE burning a run
uv run --directory ...\livekit-agent-simulator lk-sim preflight

# 4. Run the bundled smoke scenario (2 turns, 90s cap)
uv run --directory ...\livekit-agent-simulator lk-sim run smoke-hello

# 5. Inspect
uv run --directory ...\livekit-agent-simulator lk-sim report <run-id>
uv run --directory ...\livekit-agent-simulator lk-sim log <run-id> --kind "transcript.*"
uv run --directory ...\livekit-agent-simulator lk-sim log <run-id> --kind "tool.*"
```

## What success looks like

- `dispatch.agent_joined` appears in the log within `agent_join_timeout_ms`.
- `sim.gemini_connected`, `sim.mic_published`, `sim.agent_audio_bridged` events exist.
- `transcript.agent.final` (from `lk.transcription`) and `transcript.user.final`
  (from the sim's own Gemini transcription) alternate per turn.
- `reports/<run-id>/timeline.md` reads like a call narrative; `summary.json` has
  turn-taking percentiles and (if PassCriteria set) a judge verdict.

## Common failures

| Symptom | Meaning |
|---|---|
| `Preflight failed: livekit.api ... 401` | Wrong api_key/api_secret or URL |
| `Agent ... did not join room` | Worker not running, or `agent_name` mismatch |
| `sim.error where=gemini->lk ... 1011` | Wrong Live model name or key lacks Live API access |
| `dead_call_silence` end reason | Agent joined but never spoke — check worker logs |
| No `tool.*` events | Worker doesn't publish matching data topics — adjust `observe.tool_event_patterns` |

## Testing against voice-ai-worker specifically

`observe.data_topics` defaults in the template already match the worker's
`voice_ai.flow` / `voice_ai.transcript` topics. Tune `tool_event_patterns` to the
actual `type` values the worker publishes (see `src/agent/flow/publish-flow-event.ts`
in the worker repo).
