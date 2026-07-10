# livekit-agent-simulator

Standalone MCP server + CLI (`lk-sim`) that dials **any LiveKit voice agent** with an
AI simulated caller (Gemini Live) and records a full forensic behavior log —
transcripts, tool events, flow events, room events — all timestamped per turn.

**Zero-touch:** the agent under test is a black box. The simulator only needs the
agent's registered `agent_name`; it never reads or modifies the target project's code,
`.env`, or model config.

## How it works

1. Reads `<your-repo>/.agent-sim/config.yaml` (LiveKit creds + `agent_name` + simulator voice).
2. Creates a fresh room `lk-sim-<run-id>` and dispatches the agent via `RoomAgentDispatch`.
3. Joins as participant `lk-sim-caller`, bridges audio with a Gemini Live session
   (`gemini-3.1-flash-live-preview`) playing the scenario persona.
4. Observes everything from inside the room: `lk.transcription` text streams, custom
   data topics (e.g. `voice_ai.flow`), audio timing, interruptions, silences.
5. Writes `reports/<run-id>/` — `events.jsonl`, `timeline.md`, `summary.json`,
   `meta.json` — and mirrors to `runs.sqlite`.
6. Optional LLM judge (`gemini-2.5-flash`) scores the transcript + tool spans against
   the scenario's PassCriteria.

## Quick start

```bash
# In the repo you want to test (worker must be running with its agent_name):
uv run --directory /path/to/livekit-agent-simulator lk-sim init
#   → scaffolds .agent-sim/ (gitignored) — fill in config.yaml

uv run --directory /path/to/livekit-agent-simulator lk-sim run smoke-hello
uv run --directory /path/to/livekit-agent-simulator lk-sim report <run-id>
```

## Cursor MCP config

```json
{
  "mcpServers": {
    "livekit-agent-simulator": {
      "command": "uv",
      "args": ["run", "--directory", "/abs/path/livekit-agent-simulator", "livekit-agent-simulator-mcp"]
    }
  }
}
```

## MCP tools

| Tool | Purpose |
|------|---------|
| `init_project` | Scaffold `.agent-sim/` + add to `.gitignore` |
| `list_scenarios` | Glob `scenarios/*.jsonl` |
| `validate_scenario` | Schema + lint |
| `run_scenario` | Run a simulation, returns `run_id` |
| `get_run_status` | running / done / failed + turn count |
| `get_run_log` | Read `events.jsonl` with kind/turn/source/time filters |
| `get_run_report` | Summary + judge verdict + suspicious turns |
| `compare_runs` | Diff two runs |
| `list_runs` | Run history from SQLite |

## Docs

- [AGENTS.md](AGENTS.md) — rules for AI agents (standalone repo; no worker context)
- [docs/smoke-test.md](docs/smoke-test.md) — first end-to-end run against a local worker
