"""`lk-sim` CLI — mirrors the MCP tools for humans. Defaults project root to CWD."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

import typer


def _ensure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


_ensure_utf8_stdio()

from . import ops
from .config import ConfigError
from .preflight import run_preflight
from .scenario import ScenarioError

app = typer.Typer(name="lk-sim", help="Simulate an AI caller against a LiveKit voice agent.")

ROOT_OPTION = typer.Option(None, "--root", help="Project root (default: current directory)")


def _root(root: Optional[Path]) -> Path:
    return (root or Path.cwd()).resolve()


def _print(data: Any) -> None:
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2))


def _run_failed(result: dict[str, Any]) -> bool:
    if not result.get("executed") or result.get("status") != "done":
        return True
    verdict = ((result.get("summary") or {}).get("verdict") or {}).get("verdict")
    return verdict == "fail"


def _run(coro: Any) -> Any:
    try:
        return asyncio.run(coro)
    except (ConfigError, ScenarioError, RuntimeError) as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command()
def init(root: Optional[Path] = ROOT_OPTION) -> None:
    """Scaffold .agent-sim/ in the target repo."""
    _print(ops.init_project(_root(root)))


@app.command()
def preflight(root: Optional[Path] = ROOT_OPTION) -> None:
    """Check config + LiveKit connectivity without running a scenario."""
    result, _ = _run(run_preflight(_root(root)))
    _print({"ok": result.ok, "checks": result.checks})
    if not result.ok:
        raise typer.Exit(1)


@app.command("scenarios")
def scenarios_cmd(root: Optional[Path] = ROOT_OPTION) -> None:
    """List scenarios."""
    try:
        _print(ops.list_scenarios(_root(root)))
    except ConfigError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command()
def plugins(root: Optional[Path] = ROOT_OPTION) -> None:
    """List verify plugins (.agent-sim/plugins + entry-points)."""
    try:
        _print(ops.list_plugins(_root(root)))
    except ConfigError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command()
def validate(scenario_id: str, root: Optional[Path] = ROOT_OPTION) -> None:
    """Validate one scenario."""
    result = ops.validate_scenario(_root(root), scenario_id)
    _print(result)
    if not result.get("valid"):
        raise typer.Exit(1)


@app.command()
def export(scenario_id: str, root: Optional[Path] = ROOT_OPTION) -> None:
    """Export parsed scenario JSON (Execute run params, Dispatch flag, PassCriteria)."""
    try:
        _print(ops.export_scenario(_root(root), scenario_id))
    except ConfigError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command()
def run(scenario_id: str, root: Optional[Path] = ROOT_OPTION) -> None:
    """Run a scenario end-to-end and print the summary."""
    result = _run(ops.run_scenario(_root(root), scenario_id))
    _print(result)
    if _run_failed(result):
        raise typer.Exit(1)


@app.command()
def execute(scenario_id: str, root: Optional[Path] = ROOT_OPTION) -> None:
    """Validate then execute one scenario from .agent-sim/scenarios/."""
    result = _run(ops.execute_scenario(_root(root), scenario_id))
    _print(result)
    if _run_failed(result):
        raise typer.Exit(1)


@app.command("execute-all")
def execute_all_cmd(
    tag: Optional[str] = typer.Option(None, help="Only scenarios with this tag"),
    root: Optional[Path] = ROOT_OPTION,
) -> None:
    """Execute all valid scenarios (optional tag filter)."""
    result = _run(ops.execute_scenarios(_root(root), scenario_ids=None, tag=tag))
    _print(result)
    if any(_run_failed(r) for r in result.get("results", [])):
        raise typer.Exit(1)


@app.command()
def status(run_id: str, root: Optional[Path] = ROOT_OPTION) -> None:
    """Run status from SQLite."""
    _print(_run(ops.get_run_status(_root(root), run_id)))


@app.command()
def log(
    run_id: str,
    kind: Optional[str] = typer.Option(None, help="Event kind, trailing * for prefix (tool.*)"),
    turn: Optional[int] = typer.Option(None),
    source: Optional[str] = typer.Option(None),
    limit: int = typer.Option(200),
    root: Optional[Path] = ROOT_OPTION,
) -> None:
    """Filtered view of events.jsonl."""
    try:
        _print(ops.get_run_log(_root(root), run_id, kind=kind, turn=turn, source=source, limit=limit))
    except ConfigError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command()
def report(run_id: str, root: Optional[Path] = ROOT_OPTION) -> None:
    """Summary + verdict + suspicious turns."""
    _print(_run(ops.get_run_report(_root(root), run_id)))


@app.command()
def compare(run_id_a: str, run_id_b: str, root: Optional[Path] = ROOT_OPTION) -> None:
    """Diff two runs."""
    _print(_run(ops.compare_runs(_root(root), run_id_a, run_id_b)))


@app.command()
def runs(
    limit: int = typer.Option(20),
    scenario_id: Optional[str] = typer.Option(None, "--scenario"),
    root: Optional[Path] = ROOT_OPTION,
) -> None:
    """Run history, newest first."""
    _print(_run(ops.list_runs(_root(root), limit=limit, scenario_id=scenario_id)))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
