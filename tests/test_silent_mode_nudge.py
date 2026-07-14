"""P1.B1 — silent_mode skips agent-greeted nudge; no barge under silent speech_conditions."""

from __future__ import annotations

import asyncio

import pytest

from livekit_agent_simulator.behavior_compile import compile_from_speech_conditions
from livekit_agent_simulator.caller_nudge import nudge_caller_after_agent_greeting
from livekit_agent_simulator.run_orchestrator import _persona_is_silent_mode


def test_persona_is_silent_mode_flags():
    assert _persona_is_silent_mode({"speech_conditions": {"silent_mode": True}})
    assert _persona_is_silent_mode({"traits": ["silent"]})
    assert not _persona_is_silent_mode({"traits": ["polite"]})


def test_silent_mode_skips_barge_policy():
    steps = compile_from_speech_conditions(
        {
            "speech_conditions": {
                "silent_mode": True,
                "barge_policy": "mid_agent_turn",
            }
        }
    )
    assert not any(s.barge_in for s in steps)
    assert any(s.action == "wait" and s.silence_after_cue_ms >= 500 for s in steps)


@pytest.mark.asyncio
async def test_nudge_skip_silent_emits_event():
    events = []

    class W:
        def emit(self, kind, spec=None, **kw):
            events.append((kind, spec))

    class O:
        agent_has_spoken = True
        user_has_spoken = False

    class B:
        end_call = asyncio.Event()

        async def inject_cue(self, *a, **k):
            raise AssertionError("must not inject when silent")

    await nudge_caller_after_agent_greeting(
        O(), B(), W(), first_speaker="agent", skip_silent=True
    )
    assert events and events[0][0] == "sim.agent_greeted_nudge"
    assert events[0][1].get("skipped") is True
