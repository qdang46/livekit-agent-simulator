"""Shared implementation of the 9 project operations — used by both MCP tools and CLI."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .config import DOT_FOLDER, ConfigError, load_config
from .logging.sqlite_store import RunStore
from .scenario import ScenarioError, find_scenario, list_scenarios as _list_scenarios, parse_scenario
from .scenario_from_dict import export_scenario_dict, scenario_from_dict
from . import run_orchestrator
from .preflight import run_preflight
from .plugins.loader import ensure_plugins_loaded
from .plugins.registry import list_verify_plugins

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def init_project(project_root: Path | str) -> dict[str, Any]:
    """Scaffold .agent-sim/ with config.yaml template + smoke scenario; gitignore it."""
    root = Path(project_root).resolve()
    dot = root / DOT_FOLDER
    created: list[str] = []

    (dot / "scenarios").mkdir(parents=True, exist_ok=True)
    (dot / "reports").mkdir(parents=True, exist_ok=True)
    (dot / "plugins").mkdir(parents=True, exist_ok=True)

    config_dst = dot / "config.yaml"
    if not config_dst.exists():
        shutil.copyfile(TEMPLATES_DIR / "config.yaml", config_dst)
        created.append(str(config_dst))

    smoke_dst = dot / "scenarios" / "smoke-hello.jsonl"
    if not smoke_dst.exists():
        shutil.copyfile(TEMPLATES_DIR / "smoke-hello.jsonl", smoke_dst)
        created.append(str(smoke_dst))

    plugin_dst = dot / "plugins" / "example_verify.py"
    if not plugin_dst.exists():
        shutil.copyfile(TEMPLATES_DIR / "plugins" / "example_verify.py", plugin_dst)
        created.append(str(plugin_dst))

    gitignore = root / ".gitignore"
    line = f"{DOT_FOLDER}/"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if line not in content.splitlines():
            gitignore.write_text(content.rstrip("\n") + f"\n\n# livekit-agent-simulator\n{line}\n", encoding="utf-8")
            created.append(f"{gitignore} (+{line})")
    else:
        gitignore.write_text(f"# livekit-agent-simulator\n{line}\n", encoding="utf-8")
        created.append(str(gitignore))

    return {
        "dot_dir": str(dot),
        "created": created,
        "next_steps": [
            f"Fill in LiveKit + Google credentials in {config_dst}",
            "Make sure your worker is running with the configured agent_name",
            "Run the smoke scenario: lk-sim run smoke-hello",
        ],
    }


def list_scenarios(project_root: Path | str) -> list[dict[str, Any]]:
    cfg = load_config(project_root)
    return _list_scenarios(cfg.scenarios_dir)


def validate_scenario(project_root: Path | str, scenario_id: str) -> dict[str, Any]:
    cfg = load_config(project_root)
    path = cfg.scenarios_dir / f"{scenario_id}.jsonl"
    if not path.exists():
        candidates = list(cfg.scenarios_dir.glob("*.jsonl"))
        return {
            "valid": False,
            "error": f"{path} not found",
            "available": [c.name for c in candidates],
        }
    try:
        s = parse_scenario(path)
    except ScenarioError as e:
        return {"valid": False, "error": str(e)}
    warnings: list[str] = []
    if not s.pass_criteria:
        warnings.append("No PassCriteria — judge will be skipped for this scenario.")
    run = s.run_spec
    if run.max_turns > 20:
        warnings.append(f"max_turns={run.max_turns} is unusually high.")
    if run.first_speaker == "agent" and not (s.dispatch and s.dispatch.metadata):
        warnings.append(
            "first_speaker=agent with no Dispatch.metadata — many agents wait for caller audio. "
            "Add Execute.first_speaker=user or a project-specific Dispatch.metadata JSON."
        )
    if s.plugin_modules or (s.script_verify and s.script_verify.plugins):
        load_info = ensure_plugins_loaded(cfg.project_root, s.plugin_modules)
        known = set(load_info.get("verify_plugins") or [])
        for name in (s.script_verify.plugins if s.script_verify else ()):
            if name not in known:
                warnings.append(f"verify plugin {name!r} is not registered (load errors: {load_info.get('errors')})")
        if load_info.get("errors"):
            warnings.extend(f"plugin load: {e}" for e in load_info["errors"])
    return {
        "valid": True,
        "id": s.id,
        "locale": s.locale,
        "max_turns": run.max_turns,
        "timeout_s": run.timeout_s,
        "first_speaker": run.first_speaker,
        "has_execute": s.execute is not None,
        "has_dispatch": s.dispatch is not None and bool(s.dispatch.metadata),
        "pass_criteria": s.pass_criteria,
        "warnings": warnings,
    }


def export_scenario(project_root: Path | str, scenario_id: str) -> dict[str, Any]:
    """Export parsed scenario JSON for inspection / agent-driven customization."""
    cfg = load_config(project_root)
    try:
        s = find_scenario(cfg.scenarios_dir, scenario_id)
    except ScenarioError as e:
        return {"found": False, "scenario_id": scenario_id, "error": str(e)}
    return {"found": True, **export_scenario_dict(s)}


def list_plugins(project_root: Path | str) -> dict[str, Any]:
    """List registered verify plugins after loading entry-points and local modules."""
    cfg = load_config(project_root)
    local_dir = cfg.dot_dir / "plugins"
    local_files = sorted(p.stem for p in local_dir.glob("*.py") if not p.name.startswith("_"))
    load_info = ensure_plugins_loaded(cfg.project_root, local_files)
    return {
        "verify_plugins": list_verify_plugins(),
        "local_modules": local_files,
        "load": load_info,
        "entry_point_group": "lk_sim.plugins",
    }


async def run_scenario_dict(project_root: Path | str, scenario: dict[str, Any]) -> dict[str, Any]:
    """Run a scenario built in Python (same fields as export_scenario / JSONL sections)."""
    cfg = load_config(project_root)
    preflight, _ = await run_preflight(cfg.project_root, connectivity=True)
    if not preflight.ok:
        failed = [c for c in preflight.checks if c["status"] == "fail"]
        raise RuntimeError("Preflight failed: " + "; ".join(f"{c['name']}: {c['detail']}" for c in failed))
    scenario_id = str(scenario.get("id") or (scenario.get("metadata") or {}).get("id", "dynamic"))
    s = scenario_from_dict(scenario, path=cfg.scenarios_dir / f"{scenario_id}.jsonl")
    return await run_orchestrator.run_scenario_instance(cfg, s)


async def execute_scenario_dict(project_root: Path | str, scenario: dict[str, Any]) -> dict[str, Any]:
    """Validate dict-shaped scenario then run (no JSONL file on disk required)."""
    try:
        scenario_from_dict(scenario)
    except ScenarioError as e:
        return {"executed": False, "validation": {"valid": False, "error": str(e)}}
    result = await run_scenario_dict(project_root, scenario)
    return {"executed": True, "validation": {"valid": True}, **result}


async def execute_scenario(project_root: Path | str, scenario_id: str) -> dict[str, Any]:
    """Validate then run one scenario from `.agent-sim/scenarios/<id>.jsonl`."""
    validation = validate_scenario(project_root, scenario_id)
    if not validation.get("valid"):
        return {"executed": False, "validation": validation}
    result = await run_scenario(project_root, scenario_id)
    return {"executed": True, "validation": validation, **result}


async def execute_scenarios(
    project_root: Path | str,
    scenario_ids: list[str] | None = None,
    tag: str | None = None,
) -> dict[str, Any]:
    """Run multiple scenarios. If scenario_ids omitted, runs all valid scenarios (optional tag filter)."""
    cfg = load_config(project_root)
    listed = _list_scenarios(cfg.scenarios_dir)
    if scenario_ids:
        targets = scenario_ids
    else:
        targets = [
            item["id"]
            for item in listed
            if item.get("id") and not item.get("error") and (not tag or tag in (item.get("tags") or []))
        ]
    results: list[dict[str, Any]] = []
    for sid in targets:
        try:
            results.append(await execute_scenario(project_root, sid))
        except Exception as e:
            results.append({"executed": False, "scenario_id": sid, "error": f"{type(e).__name__}: {e}"})
    return {"count": len(results), "results": results}


async def run_scenario(project_root: Path | str, scenario_id: str) -> dict[str, Any]:
    cfg = load_config(project_root)
    return await run_orchestrator.run_scenario(cfg, scenario_id)


async def get_run_status(project_root: Path | str, run_id: str) -> dict[str, Any]:
    cfg = load_config(project_root)
    run = await RunStore(cfg.sqlite_path).get_run(run_id)
    if run is None:
        return {"found": False, "run_id": run_id}
    return {
        "found": True,
        "run_id": run["run_id"],
        "status": run["status"],
        "scenario_id": run["scenario_id"],
        "room_name": run["room_name"],
        "started_utc": run["started_utc"],
        "ended_utc": run["ended_utc"],
        "duration_ms": run["duration_ms"],
        "turn_count": run["turn_count"],
        "tool_errors": run["tool_errors"],
        "report_dir": run["report_dir"],
    }


def get_run_log(
    project_root: Path | str,
    run_id: str,
    kind: str | None = None,
    turn: int | None = None,
    source: str | None = None,
    since_mono_ms: int | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Read events.jsonl with filters. `kind` supports prefix match with trailing `*`."""
    cfg = load_config(project_root)
    events_path = cfg.reports_dir / run_id / "events.jsonl"
    if not events_path.exists():
        return {"found": False, "run_id": run_id, "error": f"{events_path} not found"}

    out: list[dict[str, Any]] = []
    total = 0
    with events_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            total += 1
            if kind:
                if kind.endswith("*"):
                    if not e["kind"].startswith(kind[:-1]):
                        continue
                elif e["kind"] != kind:
                    continue
            if turn is not None and e.get("turn") != turn:
                continue
            if source and e.get("source") != source:
                continue
            if since_mono_ms is not None and e.get("ts_mono_ms", 0) < since_mono_ms:
                continue
            out.append(e)

    truncated = len(out) > limit
    return {
        "found": True,
        "run_id": run_id,
        "total_events": total,
        "matched": len(out),
        "truncated": truncated,
        "events": out[:limit],
    }


async def get_run_report(project_root: Path | str, run_id: str) -> dict[str, Any]:
    cfg = load_config(project_root)
    report_dir = cfg.reports_dir / run_id
    summary_path = report_dir / "summary.json"
    if not summary_path.exists():
        status = await get_run_status(project_root, run_id)
        return {"found": False, "run_id": run_id, "status": status}

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    meta_path = report_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    suspicious: list[dict[str, Any]] = []
    warn_ms = cfg.observe.turn_taking_warn_ms
    for t in summary.get("turns", []):
        reasons = []
        if t.get("tool_errors"):
            reasons.append(f"{t['tool_errors']} tool error(s)")
        if t.get("turn_taking_ms") is not None and t["turn_taking_ms"] > warn_ms:
            reasons.append(f"slow turn-taking {t['turn_taking_ms']}ms > {warn_ms}ms")
        if t.get("interrupted"):
            reasons.append("interrupted")
        if reasons:
            suspicious.append({**t, "reasons": reasons})

    return {
        "found": True,
        "run_id": run_id,
        "summary": summary,
        "meta": meta,
        "suspicious_turns": suspicious,
        "timeline_path": str(report_dir / "timeline.md"),
        "events_path": str(report_dir / "events.jsonl"),
    }


async def compare_runs(project_root: Path | str, run_id_a: str, run_id_b: str) -> dict[str, Any]:
    a = await get_run_report(project_root, run_id_a)
    b = await get_run_report(project_root, run_id_b)
    if not a.get("found") or not b.get("found"):
        return {"error": "one or both runs not found", "a": a.get("found"), "b": b.get("found")}

    def digest(r: dict[str, Any]) -> dict[str, Any]:
        s = r["summary"]
        return {
            "run_id": r["run_id"],
            "status": s.get("status"),
            "duration_ms": s.get("duration_ms"),
            "turn_count": s.get("turn_count"),
            "tool_errors": s.get("tool_errors"),
            "interruptions": s.get("interruptions"),
            "turn_taking_p50": (s.get("turn_taking_ms") or {}).get("p50"),
            "turn_taking_p95": (s.get("turn_taking_ms") or {}).get("p95"),
            "verdict": (s.get("verdict") or {}).get("verdict"),
        }

    da, db = digest(a), digest(b)
    deltas = {
        k: {"a": da[k], "b": db[k]}
        for k in da
        if k != "run_id" and da[k] != db[k]
    }
    return {"a": da, "b": db, "deltas": deltas}


async def list_runs(
    project_root: Path | str, limit: int = 20, scenario_id: str | None = None
) -> list[dict[str, Any]]:
    cfg = load_config(project_root)
    if not cfg.sqlite_path.exists():
        return []
    return await RunStore(cfg.sqlite_path).list_runs(limit=limit, scenario_id=scenario_id)


__all__ = [
    "ConfigError",
    "init_project",
    "list_scenarios",
    "list_plugins",
    "validate_scenario",
    "export_scenario",
    "run_scenario",
    "run_scenario_dict",
    "execute_scenario",
    "execute_scenario_dict",
    "execute_scenarios",
    "get_run_status",
    "get_run_log",
    "get_run_report",
    "compare_runs",
    "list_runs",
]
