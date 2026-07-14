"""Resolve package data paths (templates + web UI in checkout and installed wheel)."""

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


def package_web_dir() -> Path:
    """Built Vite assets for ``lk-sim web``.

    Search order:
    1. ``livekit_agent_simulator/web_static`` (wheel force-include of ``web/dist``)
    2. Repo-root ``web/dist`` (editable checkout after ``pnpm --dir web build``)
    """
    pkg_dir = Path(__file__).resolve().parent
    packaged = pkg_dir / "web_static"
    if (packaged / "index.html").is_file():
        return packaged
    cur = pkg_dir
    for _ in range(6):
        cand = cur / "web" / "dist"
        if (cand / "index.html").is_file():
            return cand
        cur = cur.parent
    return packaged
