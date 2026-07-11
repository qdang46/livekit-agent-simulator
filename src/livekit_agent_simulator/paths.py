"""Resolve package data paths (templates work in editable checkout and installed wheel)."""

from __future__ import annotations

from pathlib import Path


def package_templates_dir() -> Path:
    """Directory with config.yaml scaffold, smoke scenario, cues, example plugins.

    Search order:
    1. ``livekit_agent_simulator/templates`` next to this package (wheel force-include)
    2. Repo-root ``templates/`` (editable / monorepo checkout)
    """
    pkg_dir = Path(__file__).resolve().parent
    # Prefer package-local templates (wheel force-include), then walk up for
    # editable checkouts: <repo>/src/livekit_agent_simulator → <repo>/templates.
    cur = pkg_dir
    for _ in range(6):
        cand = cur / "templates"
        if cand.is_dir() and (cand / "config.yaml").exists():
            return cand
        cur = cur.parent
    raise FileNotFoundError(
        "livekit-agent-simulator templates not found. "
        "Expected package data or a repo-root templates/ directory with config.yaml."
    )


def package_cues_dir() -> Path:
    return package_templates_dir() / "cues"
