"""Unit tests for voice metrics aggregates (P1.3)."""

from livekit_agent_simulator.metrics import compute_voice_metrics, metrics_digest


def _ev(kind: str, mono: int, **spec):
    return {"kind": kind, "ts_mono_ms": mono, "spec": spec}


def test_empty_events():
    m = compute_voice_metrics([])
    assert m["schema"] == "agent-sim/metrics/v1"
    assert m["turn_taking_ms"]["count"] == 0
    assert m["ttfw_ms"] is None
    assert m["barge_count"] == 0
    assert m["barge_recovery_rate"] is None
    assert m["talk_ratio"] is None


def test_turn_taking_and_ttfw():
    events = [
        _ev("transcript.user.final", 1000, text="hello there"),
        _ev("transcript.agent.final", 1800, text="Hi, how can I help?", turn_taking_ms=800),
        _ev("transcript.user.final", 3000, text="book me"),
        _ev("transcript.agent.final", 5200, text="Sure.", turn_taking_ms=2200),
    ]
    m = compute_voice_metrics(events)
    assert m["ttfw_ms"] == 1800
    assert m["ttfw_source"] == "transcript.agent.final"
    assert m["turn_taking_ms"]["count"] == 2
    assert m["turn_taking_ms"]["p50"] == 800
    assert m["turn_taking_ms"]["max"] == 2200
    assert m["agent_finals"] == 2
    assert m["user_finals"] == 2
    assert m["talk_ratio"] is not None
    assert 0 < m["talk_ratio"] < 1
    d = metrics_digest(m)
    assert d["ttfw_ms"] == 1800
    assert d["turn_p50_ms"] == 800


def test_ttfw_from_preamble():
    events = [
        _ev("transcript.agent.preamble", 400, text="Welcome!"),
        _ev("transcript.user.final", 1000, text="hi"),
        _ev("transcript.agent.final", 1500, text="yes", turn_taking_ms=500),
    ]
    m = compute_voice_metrics(events)
    assert m["ttfw_ms"] == 400
    assert m["ttfw_source"] == "transcript.agent.preamble"


def test_barge_recovery():
    events = [
        _ev("sim.script.cue", 1000, barge_in=True, step_id="cut"),
        _ev("interruption", 1000, by="sim", barge_in=True),
        _ev("transcript.agent.final", 2500, text="Sorry, go on."),
        _ev("sim.script.cue", 4000, barge_in=True),
        # no recovery after second barge
    ]
    m = compute_voice_metrics(events)
    assert m["barge_count"] == 2  # deduped cue+interruption at 1000, plus 4000
    assert m["barges_recovered"] == 1
    assert m["barge_recovery_rate"] == 0.5
    assert m["recovery_ms"]["count"] == 1
    assert m["recovery_ms"]["p50"] == 1500


def test_tool_error_rate_and_slow_turns():
    events = [
        _ev("tool.start", 100, name="a"),
        _ev("tool.start", 200, name="b"),
        _ev("tool.error", 300, name="b"),
        _ev("transcript.agent.final", 400, text="x", turn_taking_ms=3000),
        _ev("transcript.agent.final", 500, text="y", turn_taking_ms=6000),
    ]
    m = compute_voice_metrics(events)
    assert m["tool_calls"] == 2
    assert m["tool_errors"] == 1
    assert m["tool_error_rate"] == 0.5
    assert m["slow_turns_over_2500ms"] == 2
    assert m["slow_turns_over_5000ms"] == 1
