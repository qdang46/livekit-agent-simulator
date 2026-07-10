"""Example verify plugin — copy to `<repo>/.agent-sim/plugins/` and reference from scenario JSONL."""

from __future__ import annotations

from livekit_agent_simulator.plugins import VerifyContext, verify_plugin


@verify_plugin("example_backchannel_continue")
def example_backchannel_continue(ctx: VerifyContext) -> dict:
    """Pass when agent spoke again after the scripted backchannel cue."""
    min_finals = int(ctx.options.get("min_agent_finals", 1))
    actual = ctx.finals_after_first_cue("agent")
    return {
        "pass": actual >= min_finals,
        "checks": [
            {
                "check": "agent_finals_after_cue",
                "pass": actual >= min_finals,
                "expected": min_finals,
                "actual": actual,
            }
        ],
        "detail": "example plugin — replace with your project logic",
    }


def setup() -> None:
    """Optional: called when this module is loaded from `.agent-sim/plugins/`."""
    pass
