"""Unit tests for caller dialog policy (Strategy + Composite sections)."""

from __future__ import annotations

from livekit_agent_simulator.caller import build_persona_system_instruction
from livekit_agent_simulator.caller.default_policy import DefaultCallerPolicy
from livekit_agent_simulator.caller.policy import CallerPolicyContext, MidcallCue
from livekit_agent_simulator.caller.prompt_sections import (
    ConstraintsSection,
    GoalsSection,
    GuardrailsSection,
    RoleSection,
    ScriptTimingSection,
)


def test_role_section_includes_locale():
    sec = RoleSection()
    lines = sec.render(CallerPolicyContext(persona={"name": "Sam"}, locale="vi-VN"))
    joined = "\n".join(lines)
    assert "RESPOND IN vi-VN" in joined
    assert "HUMAN" in joined
    assert "Sam" in joined


def test_goals_section_creates_checklist():
    ctx = CallerPolicyContext(persona={"goals": ["A", "B"]}, locale="en")
    lines = GoalsSection().render(ctx)
    joined = "\n".join(lines)
    assert "GOAL 1" in joined
    assert "GOAL 2" in joined
    assert "Do NOT say goodbye" in joined


def test_constraints_section_adds_examples():
    ctx = CallerPolicyContext(
        persona={"constraints": ["No card numbers"]}, locale="en"
    )
    lines = ConstraintsSection().render(ctx)
    joined = "\n".join(lines)
    assert "HARD CONSTRAINTS" in joined
    assert "card number" in joined.lower()


def test_guardrails_present():
    ctx = CallerPolicyContext(persona={"goals": ["Ask about order"]}, locale="en")
    lines = GuardrailsSection().render(ctx)
    joined = "\n".join(lines)
    assert "GUARDRAILS" in joined
    assert "[END_CALL]" in joined
    assert 'NEVER pronounce the English words "end call"' in joined


def test_script_timing_forbids_early_bye():
    ctx = CallerPolicyContext(
        persona={"goals": ["Ask fee"]},
        locale="en",
        script_steps=[{"id": "open"}, {"id": "bye"}],
    )
    joined = "\n".join(ScriptTimingSection().render(ctx))
    assert "simulator-owned" in joined.lower() or "INTERACTION TIMING" in joined
    assert "Do NOT say goodbye" in joined
    assert "Freestyle farewell" in joined


def test_guardrails_script_mode_skips_freestyle_end_call_marker():
    ctx = CallerPolicyContext(
        persona={"goals": ["Ask fee"]},
        locale="en",
        script_steps=[{"id": "bye"}],
    )
    joined = "\n".join(GuardrailsSection().render(ctx))
    assert "A timed Script is active" in joined
    assert "append the exact harness marker" not in joined


def test_build_persona_system_instruction_facade():
    prompt = build_persona_system_instruction(
        persona={
            "name": "Sam",
            "brief": "Test caller",
            "goals": ["Confirm support", "End call"],
            "constraints": ["No card numbers"],
        },
        locale="en-US",
        first_speaker="agent",
    )
    assert "PERSONA" in prompt
    assert "GOAL 1" in prompt
    assert "HARD CONSTRAINTS" in prompt
    assert "GUARDRAILS" in prompt
    assert "Sam" in prompt
    # first_speaker agent → wait mark
    assert "Wait for the assistant" in prompt


def test_default_policy_midcall_goals_bootstrap():
    policy = DefaultCallerPolicy()
    # We call through context without script_inject
    ctx = CallerPolicyContext(
        persona={"goals": ["Find my order", "Cancel"], "brief": "test"},
        locale="en-US",
        first_speaker="user",
    )
    cues = policy.midcall_cues(ctx)
    # user speaker → bootstrap
    boot = [c for c in cues if c.kind == "bootstrap"]
    regd = [c for c in cues if c.kind == "reground"]
    assert len(boot) >= 1
    assert len(regd) >= 1
    assert "speak first" in boot[0].text.lower()
    assert "GOAL 1" in regd[0].text
    assert isinstance(cues[0], MidcallCue)


def test_default_policy_midcall_script_no_early_bye():
    policy = DefaultCallerPolicy()
    ctx = CallerPolicyContext(
        persona={"goals": ["Fee"], "brief": "test"},
        locale="en-US",
        first_speaker="agent",
        script_steps=[{"id": "open"}, {"id": "bye"}],
    )
    cues = policy.midcall_cues(ctx)
    script_rg = [c for c in cues if c.label == "script_no_early_bye"]
    assert len(script_rg) == 1
    assert "Do not say bye" in script_rg[0].text
