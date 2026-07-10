# AGENTS.md — livekit-agent-simulator

**Standalone repo.** MCP + CLI that dials **any** LiveKit voice agent from a target project's
`.agent-sim/` folder. This package does **not** live inside voice-ai-worker or the dashboard.

---

## Boundary (read first)

| In scope (this repo) | Out of scope |
|---|---|
| `src/livekit_agent_simulator/` | voice-ai-worker source, dashboard tRPC, Prisma |
| `.agent-sim/` layout, scenario JSONL schema | Target agent's model stack, `.env`, tools |
| LiveKit dispatch + sim caller + behavior log | Project-specific dispatch key names in core code |
| Gemini sim + judge (keys in target `.agent-sim/config.yaml`) | Reading or modifying the agent under test |

**Zero-touch:** the agent under test is a black box. We only need `agent_name` + optional opaque
`dispatch_metadata` / scenario `Dispatch.metadata`.

**Do not** treat voice-ai-worker (or any single consumer) as default context:

- Do **not** load `voice-ai-worker/AGENTS.md`, worker `.env`, or dashboard SPEC when working here.
- Do **not** hardcode `customAgentId`, `voice_ai.flow`, or other worker-only keys in core Python.
- **Do** keep worker/dashboard examples in **target** `.agent-sim/scenarios/*.jsonl` or local docs
  under the consumer repo — not in this package's defaults.

Project-specific wiring belongs in the **target repo's** `.agent-sim/` (gitignored), via:

- `config.yaml` → `livekit.dispatch_metadata` (opaque JSON string)
- scenario line → `{"kind":"Dispatch","spec":{"metadata":"..."}}`

The simulator passes metadata through; it never interprets project keys.

---

## Repositories (relationship)

```
livekit-agent-simulator/     ← YOU ARE HERE (Python package, MCP, lk-sim CLI)
  └── installs into any target repo via MCP project_root

<target-repo>/               e.g. voice-ai-worker, a customer's app
  └── .agent-sim/            config, scenarios, reports, runs.sqlite (gitignored)
```

When the user `@`-mentions a worker path, that is only the **test target** (`project_root`), not
source code to edit unless they explicitly ask to change the worker.

---

## Default workflow

1. Read this file.
2. Identify whether the task touches **this package** or a **target** `.agent-sim/` only.
3. For protocol/SDK questions: LiveKit MCP + Exa + `livekit-agent-simulator/.venv` packages —
   not worker `node_modules`.
4. Plan impact → minimal diff → `uv run pytest -q` before done.
5. Bug fixes: research with Exa / LiveKit docs first; do not guess wire formats.

### When to plan before coding

| Task | Approach |
|---|---|
| Bug in sim/MCP/logging | Exa + LiveKit MCP → fix in this repo → pytest |
| New MCP tool / scenario kind | Short plan in chat or `docs/plans/PLAN-…md` if large |
| Target scenario/config only | Edit `<target>/.agent-sim/` — no package release needed |
| Typo, test, single-line fix | Code immediately |

No mandatory 4-agent swarm for this repo unless the user asks for deep investigation.

---

## Layout

| Path | Role |
|---|---|
| `src/livekit_agent_simulator/config.py` | Load `.agent-sim/config.yaml` |
| `src/livekit_agent_simulator/scenario.py` | JSONL schema: Persona, Execute, Dispatch, PassCriteria |
| `src/livekit_agent_simulator/ops.py` | Shared MCP + CLI operations |
| `src/livekit_agent_simulator/run_orchestrator.py` | End-to-end run |
| `src/livekit_agent_simulator/livekit/` | Room create, dispatch, observer |
| `src/livekit_agent_simulator/gemini/` | Sim caller bridge + judge |
| `src/livekit_agent_simulator/logging/` | Event envelope, SQLite, reports |
| `src/livekit_agent_simulator/mcp_server.py` | FastMCP tools |
| `src/livekit_agent_simulator/cli.py` | `lk-sim` |
| `templates/` | Init scaffolds for `.agent-sim/` |
| `docs/smoke-test.md` | First end-to-end run |
| `tests/` | pytest |

---

## MCP tools

All tools take `project_root` = absolute path to the **target** repo (where `.agent-sim/` lives).

| Tool | Purpose |
|---|---|
| `init_project` | Scaffold `.agent-sim/` |
| `list_scenarios` | Glob `scenarios/*.jsonl` |
| `validate_scenario` | Schema lint |
| `export_scenario` | Parsed scenario JSON for customization |
| `execute_scenario` | Validate + run one scenario |
| `execute_scenarios` | Batch run (optional tag filter) |
| `run_scenario` | Run without pre-validate (alias) |
| `get_run_status` / `get_run_log` / `get_run_report` | Inspect runs |
| `compare_runs` / `list_runs` | History |

Cursor config example lives in the **target** repo: `<target>/.cursor/mcp.json` pointing `uv run`
at this package directory.

---

## Scenario JSONL (agent-sim/v1)

```
Scenario → Persona → [Context] → [Simulator] → [Execute] → [Dispatch] → [PassCriteria]
```

- **Execute** — run params (`max_turns`, `timeout_s`, `first_speaker`); overrides Simulator.
- **Dispatch** — opaque `metadata` JSON for `RoomAgentDispatch` (project defines keys).
- **PassCriteria** — judge rubric (optional).

Export API: `export_scenario(project_root, scenario_id)` returns structured JSON without secrets.

---

## Verification

From **this repo root**:

```bash
uv sync --extra dev
uv run pytest -q
```

For a smoke run against a target (worker must be running separately):

```bash
uv run lk-sim preflight --root /path/to/target
uv run lk-sim execute smoke-hello --root /path/to/target
```

---

## Research order (bugs / SDK)

1. Exa (or web) for errors and prior art — **do not manual-guess fixes**
2. LiveKit MCP (`docs_search`, `get_pages`) for dispatch, text streams, audio
3. Installed SDK in `.venv`: `livekit`, `livekit-api`, `google-genai`
4. This repo's `src/` and the failing run's `reports/<run-id>/events.jsonl`

---

## Hard rules

- **No target-repo code changes** unless the user explicitly asks to edit that repo.
- **No dashboard/worker env vars** in this package's `pyproject.toml` or core config schema.
- **dispatch_metadata is opaque** — never parse project-specific keys in Python core.
- **Credentials** live in target `.agent-sim/config.yaml` (gitignored), not committed here.
- After edits: **pytest must pass** before reporting done.

---

## Naming

| Item | Value |
|---|---|
| Package / repo | `livekit-agent-simulator` |
| CLI | `lk-sim` |
| MCP server entry | `livekit-agent-simulator-mcp` |
| Dot folder (in target) | `.agent-sim/` |
| Sim participant | `lk-sim-caller` |
| Room prefix | `lk-sim-<run-id>` |
