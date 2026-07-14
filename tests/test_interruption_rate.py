"""P1.K — speech_conditions.interruption_rate soft barge series (Coval-style)."""

from __future__ import annotations

from livekit_agent_simulator.behavior_compile import compile_from_speech_conditions
from livekit_agent_simulator.script.models import counts_for_recovery_barge


def test_rate_high_adds_multiple_barges():
    steps = compile_from_speech_conditions(
        {"speech_conditions": {"interruption_rate": "high", "barge_say": "Hold on"}}
    )
    barges = [
        s
        for s in steps
        if counts_for_recovery_barge(barge_in=s.barge_in, interrupt_class=s.interrupt_class)
    ]
    assert len(barges) >= 3
    assert all(s.interrupt_class == "correction" for s in barges)


def test_rate_none_no_extra():
    steps = compile_from_speech_conditions(
        {"speech_conditions": {"interruption_rate": "none"}}
    )
    assert not any(s.barge_in for s in steps)


def test_rate_with_barge_policy_does_not_duplicate_first():
    steps = compile_from_speech_conditions(
        {
            "speech_conditions": {
                "barge_policy": "mid_agent_turn",
                "interruption_rate": "medium",
                "barge_say": "Wait",
            }
        }
    )
    barges = [s for s in steps if s.barge_in]
    # barge_policy adds 1; medium wants 2 total → one rate barge may add
    assert len(barges) >= 2
    ids = [s.id for s in barges]
    assert "auto-barge-1" in ids
