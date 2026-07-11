# livekit-agent-simulator

Standalone MCP server + CLI (`lk-sim`) that dials **any LiveKit voice agent** with an
AI simulated caller (Gemini Live) and records a full forensic behavior log —
transcripts, tool events, flow events, room events — all timestamped per turn.

**Zero-touch:** the agent under test is a black box. The simulator only needs the
agent's registered `agent_name`; it never reads or modifies the target project's code,
`.env`, or model config.

CLI and MCP expose the **same public ops** (shared `ops.py`). No duplicate “run vs execute”
paths — use `execute_*` to validate then run.

## How it works

1. Reads `<your-repo>/.agent-sim/config.yaml` (LiveKit creds + `agent_name` + simulator voice).
2. Creates a fresh room `lk-sim-<run-id>` and dispatches the agent via `RoomAgentDispatch`.
3. Joins as participant `lk-sim-caller`, bridges audio with a Gemini Live session
   (`gemini-3.1-flash-live-preview`) playing the scenario persona.
4. Observes everything from inside the room: `lk.transcription` text streams, custom
   data topics (when configured), audio timing, interruptions, silences.
5. Writes `reports/<run-id>/` — `events.jsonl`, `timeline.md`, `summary.json`,
   `meta.json`, optional `conversation.wav` — and mirrors to `runs.sqlite`.
6. Optional LLM judge (`gemini-2.5-flash`) scores the transcript + tool spans against
   the scenario's PassCriteria.

## Install (user machine)

**Download only — no uv/pip/build on your machine.** CI ships a portable pack
(embedded Python + deps + report player). The installer unzips it and adds `lk-sim` to PATH.

```bash
# macOS / Linux (from release asset — preferred)
curl -fsSL "https://github.com/quangdang46/livekit-agent-simulator/releases/download/v0.1.0/install.sh" | bash -s -- --verify
```

```powershell
# Windows PowerShell (from release asset — preferred)
irm "https://github.com/quangdang46/livekit-agent-simulator/releases/download/v0.1.0/install.ps1" -OutFile "$env:TEMP\lk-sim-install.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\lk-sim-install.ps1" -Verify
```

Then:

```bash
lk-sim guide
lk-sim web --root /path/to/target   # no Node — report player is prebuilt into the package
```

Installer options:

```bash
curl -fsSL "https://github.com/quangdang46/livekit-agent-simulator/releases/download/v0.1.0/install.sh" | bash -s -- --ref v0.1.0 --verify
curl -fsSL "https://github.com/quangdang46/livekit-agent-simulator/releases/download/v0.1.0/install.sh" | bash -s -- --no-mcp
curl -fsSL "https://github.com/quangdang46/livekit-agent-simulator/releases/download/v0.1.0/install.sh" | bash -s -- --uninstall
```

```powershell
.\install.ps1 -GitRef v0.1.0 -Verify
.\install.ps1 -NoMcp
.\install.ps1 -Uninstall
```

By default the installer also registers the **MCP** server `livekit-agent-simulator`
as **`lk-sim mcp`** into common AI coding tools (Claude Code, Cursor, Cline,
Windsurf, VS Code Copilot, Gemini CLI, Amazon Q, OpenCode, Codex, Warp when present).

### Report player (maintainers)

Source: `web/` (Vite + TypeScript). **Users never run this** — CI builds into
the portable pack / wheel.

```bash
pnpm --dir web install
pnpm --dir web build    # → templates/report-player/ (served by lk-sim web)
pnpm --dir web dev      # HMR; proxy /api + /runs → lk-sim web on :8765
```

### Release (maintainers)

```bash
# after main is green:
git tag -f v0.1.0 && git push origin main && git push origin v0.1.0 --force
# → GitHub Actions:
#    wheel + portable packs (windows-x64, linux-x64, macos-arm64, macos-x64)
#    assets: install.sh + install.ps1 + lk-sim-*.zip + *.whl
# Keep single version 0.1.0 while pre-1.0 (force-retag).
```

## Quick start

```bash
# In the repo you want to test (agent worker must be running; set `agent_name` in config):
lk-sim init --root /path/to/target
#   → scaffolds .agent-sim/ (gitignored) — fill in config.yaml

lk-sim preflight --root /path/to/target
lk-sim execute smoke-hello --root /path/to/target
lk-sim report <run-id> --root /path/to/target
lk-sim web --root /path/to/target          # audio + transcript player (Ctrl+C to stop)
```

## MCP (after install)

Installer writes the MCP command when tools are detected. Manual Cursor example:

```json
{
  "mcpServers": {
    "livekit-agent-simulator": {
      "command": "lk-sim",
      "args": ["mcp"],
      "env": {}
    }
  }
}
```

Equivalent one-shot entry: `lk-sim-mcp` (same process as `lk-sim mcp`).

Dev checkout (package not installed globally):

```json
{
  "mcpServers": {
    "livekit-agent-simulator": {
      "command": "uv",
      "args": ["run", "--directory", "/abs/path/livekit-agent-simulator", "lk-sim", "mcp"]
    }
  }
}
```


## Public ops (CLI ↔ MCP)

| CLI | MCP tool | Purpose |
|-----|----------|---------|
| `init` | `init_project` | Scaffold `.agent-sim/` + gitignore |
| `guide` | `guide` | On-demand setup/ops guide (markdown) |
| `web` | `web` | Local report player (audio + transcript sync) |
| `preflight` | `preflight` | Config + LiveKit connectivity |
| `scenarios` | `list_scenarios` | List `scenarios/*.jsonl` |
| `plugins` | `list_plugins` | Verify plugins |
| `validate` | `validate_scenario` | Schema + lint |
| `export` | `export_scenario` | Parsed scenario JSON |
| `scenario-init` | `init_scenario` | Scaffold `.jsonl` with `//` guides + examples |
| `execute` | `execute_scenario` | Validate then run one JSONL scenario |
| `execute-all` | `execute_scenarios` | Batch (optional ids / tag) |
| `execute-dict` | `execute_scenario_dict` | Validate then run in-memory dict |
| `status` | `get_run_status` | SQLite run status |
| `log` | `get_run_log` | Filtered `events.jsonl` |
| `report` | `get_run_report` | Summary + verdict + audio path |
| `compare` | `compare_runs` | Diff two runs |
| `runs` | `list_runs` | Run history |

## Docs

- [AGENTS.md](AGENTS.md) — rules for AI agents (research loop, package boundary)
- [docs/smoke-test.md](docs/smoke-test.md) — first end-to-end run
- [docs/portability.md](docs/portability.md) — consumer-specific dispatch / observe setup
- [docs/plugins.md](docs/plugins.md) — verify plugins + Python API

## CI / Release

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| [CI](.github/workflows/ci.yml) | PR / push → `main` | pnpm report-player build, `pytest` (3.10 + 3.12), `lk-sim --help` |
| [Release](.github/workflows/release.yml) | tag `v*` | pytest → wheel → **portable packs** (win/linux/mac) → GitHub Release |

Local check:

```bash
uv sync --extra dev
pnpm --dir web build
uv run pytest -q
```

Release:

```bash
git tag v0.1.0
git push origin v0.1.0
```
