"""Tests for tool/session parsing in report player cues."""

from __future__ import annotations

import json
from pathlib import Path

from livekit_agent_simulator.web.cues import build_cues_payload
from livekit_agent_simulator.web.tool_events import (
    _build_session_summary,
    _build_tool_spans,
    _extract_chat_history,
    _tool_spans_to_markers,
)


def _base_events() -> list[dict]:
    return [
        {"kind": "run.started", "ts_mono_ms": 0, "turn": 0, "source": "mcp", "spec": {}},
        {
            "event_id": "evt_tool_start",
            "kind": "tool.start",
            "ts_mono_ms": 6000,
            "turn": 2,
            "source": "lk.agent.session",
            "spec": {
                "call_id": "fc_1",
                "name": "check_inventory",
                "arguments": '{"model":"105"}',
            },
        },
        {
            "event_id": "evt_tool_end",
            "kind": "tool.end",
            "ts_mono_ms": 6400,
            "turn": 2,
            "source": "lk.agent.session",
            "parent_event_id": "evt_tool_start",
            "spec": {
                "call_id": "fc_1",
                "name": "check_inventory",
                "output": '"not found"',
                "is_error": False,
                "duration_ms": 340,
            },
        },
    ]


def test_build_tool_spans_paired() -> None:
    spans = _build_tool_spans(_base_events(), t0=2000, duration_ms=20000)
    assert len(spans) == 1
    span = spans[0]
    assert span["name"] == "check_inventory"
    assert span["start_ms"] == 4000
    assert span["end_ms"] >= span["start_ms"] + 120
    assert span["duration_ms"] == 340
    assert span["is_error"] is False
    assert span["arguments"] == '{"model":"105"}'


def test_build_tool_spans_orphan_start() -> None:
    events = [
        {
            "event_id": "evt_only",
            "kind": "tool.start",
            "ts_mono_ms": 5000,
            "turn": 1,
            "source": "lk.agent.session",
            "spec": {"name": "lookup", "call_id": "fc_x"},
        }
    ]
    spans = _build_tool_spans(events, t0=0, duration_ms=10000)
    assert len(spans) == 1
    assert spans[0]["start_ms"] == 5000
    assert spans[0]["end_ms"] == 5500


def test_build_tool_spans_error() -> None:
    events = [
        {
            "event_id": "evt_s",
            "kind": "tool.start",
            "ts_mono_ms": 3000,
            "turn": 1,
            "source": "lk.agent.session",
            "spec": {"call_id": "fc_err", "name": "bad_tool"},
        },
        {
            "kind": "tool.error",
            "ts_mono_ms": 3500,
            "turn": 1,
            "source": "lk.agent.session",
            "parent_event_id": "evt_s",
            "spec": {
                "call_id": "fc_err",
                "name": "bad_tool",
                "is_error": True,
                "error": "timeout",
                "duration_ms": 500,
            },
        },
    ]
    spans = _build_tool_spans(events, t0=0, duration_ms=None)
    assert len(spans) == 1
    assert spans[0]["is_error"] is True
    assert spans[0]["error"] == "timeout"
    markers = _tool_spans_to_markers(spans)
    assert markers[0]["type"] == "tool_error"


def test_session_summary_and_chat_history() -> None:
    events = [
        {
            "kind": "session.agent_state",
            "ts_mono_ms": 4000,
            "spec": {"old_state": "AS_LISTENING", "new_state": "AS_THINKING"},
        },
        {
            "kind": "session.usage",
            "ts_mono_ms": 9000,
            "spec": {"model_usage": [{"llm": {"input_tokens": 12}}]},
        },
        {
            "kind": "session.chat_history",
            "ts_mono_ms": 12000,
            "spec": {"items": [{"type": "message", "role": "ASSISTANT", "content": []}]},
        },
    ]
    summary = _build_session_summary(events, t0=2000, duration_ms=20000)
    assert summary is not None
    assert summary["usage"]["model_usage"][0]["llm"]["input_tokens"] == 12
    assert summary["state_transitions"][0]["to"] == "AS_THINKING"
    assert summary["state_transitions"][0]["at_ms"] == 2000

    history = _extract_chat_history(events)
    assert history is not None
    assert history[0]["type"] == "message"


def test_build_cues_payload_includes_tools(tmp_path: Path) -> None:
    rd = tmp_path / "tool-run-20260713-120000-abcd"
    rd.mkdir()
    (rd / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in _base_events()) + "\n",
        encoding="utf-8",
    )
    (rd / "meta.json").write_text(
        json.dumps(
            {
                "scenario_id": "mcp-tool-smoke-test",
                "audio": {"duration_ms": 20000, "t0_mono_ms": 2000},
                "config_snapshot": {"observe": {"observe_gaps": []}},
            }
        ),
        encoding="utf-8",
    )
    (rd / "summary.json").write_text(
        json.dumps({"tool_calls": 1, "tool_errors": 0}),
        encoding="utf-8",
    )
    payload = build_cues_payload(rd)
    assert payload["tool_summary"]["tool_count"] == 1
    assert payload["tool_events"][0]["name"] == "check_inventory"
    assert "tool" in payload["marker_counts"]
    assert payload["observe_gaps"] == []
