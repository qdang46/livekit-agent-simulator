"""Tool + session events → report player spans and summaries."""

from __future__ import annotations

from typing import Any

from .report_time import (
    MARKER_TOOL,
    MARKER_TOOL_ERROR,
    _clamp_end,
    _mono_to_audio_ms,
)

_UNCLOSED_TOOL_TAIL_MS = 500
_TOOL_BAND_MIN_MS = 400
_TOOL_BAND_CAP_MS = 400


def _spec_str(spec: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        val = spec.get(key)
        if val is None:
            continue
        text = str(val).strip()
        if text:
            return text
    return None


def _pending_key(spec: dict[str, Any], event_id: str) -> str:
    call_id = _spec_str(spec, "call_id", "id")
    if call_id:
        return f"call:{call_id}"
    return f"evt:{event_id}"


def _resolve_end_ms(
    start_ms: int,
    duration_ms: int | None,
    duration_cap: int | None,
) -> int:
    if duration_ms is not None and duration_ms > 0:
        span = min(duration_ms, _TOOL_BAND_CAP_MS) if duration_cap else duration_ms
        return start_ms + max(_TOOL_BAND_MIN_MS, span)
    return start_ms + _UNCLOSED_TOOL_TAIL_MS


def _build_tool_spans(
    events: list[dict[str, Any]],
    t0: int,
    duration_ms: int | None,
) -> list[dict[str, Any]]:
    """Pair tool.start with tool.end / tool.error into audio-aligned spans."""
    pending: dict[str, dict[str, Any]] = {}
    spans: list[dict[str, Any]] = []

    for e in events:
        kind = str(e.get("kind") or "")
        if kind not in ("tool.start", "tool.end", "tool.error"):
            continue
        try:
            mono = int(e.get("ts_mono_ms") or 0)
        except (TypeError, ValueError):
            continue
        start = _mono_to_audio_ms(mono, t0, duration_ms)
        if start is None:
            continue

        spec = e.get("spec") if isinstance(e.get("spec"), dict) else {}
        event_id = str(e.get("event_id") or "")
        turn = e.get("turn")
        source = str(e.get("source") or "") or None
        name = _spec_str(spec, "name", "tool_name") or "tool"
        arguments = _spec_str(spec, "arguments", "args", "payload")
        call_id = _spec_str(spec, "call_id", "id")

        if kind == "tool.start":
            key = _pending_key(spec, event_id)
            pending[key] = {
                "call_id": call_id,
                "name": name,
                "start_ms": start,
                "turn": turn,
                "source": source,
                "arguments": arguments,
                "parent_event_id": event_id or None,
                "start_event_id": event_id or None,
            }
            continue

        parent_id = str(e.get("parent_event_id") or "")
        match_key: str | None = None
        if call_id:
            ck = f"call:{call_id}"
            if ck in pending:
                match_key = ck
        if match_key is None and parent_id:
            for key, row in pending.items():
                if row.get("start_event_id") == parent_id:
                    match_key = key
                    break
        if match_key is None and len(pending) == 1:
            match_key = next(iter(pending))

        start_row = pending.pop(match_key, None) if match_key else None
        base_start = int(start_row["start_ms"]) if start_row else start
        try:
            dur = int(spec.get("duration_ms") or 0)
        except (TypeError, ValueError):
            dur = 0
        if dur <= 0 and start_row:
            dur = max(0, start - base_start)

        is_error = kind == "tool.error" or bool(spec.get("is_error"))
        output = _spec_str(spec, "output", "result", "error")
        error = _spec_str(spec, "error", "message") if is_error else None
        end_ms = _resolve_end_ms(base_start, dur if dur > 0 else None, _TOOL_BAND_CAP_MS)
        end_ms = _clamp_end(base_start, end_ms, duration_ms)

        spans.append(
            {
                "call_id": call_id or (start_row or {}).get("call_id"),
                "name": name or (start_row or {}).get("name") or "tool",
                "start_ms": base_start,
                "end_ms": end_ms,
                "duration_ms": dur if dur > 0 else None,
                "turn": turn if turn is not None else (start_row or {}).get("turn"),
                "source": source or (start_row or {}).get("source"),
                "arguments": arguments or (start_row or {}).get("arguments"),
                "output": output,
                "is_error": is_error,
                "error": error,
                "parent_event_id": parent_id or (start_row or {}).get("parent_event_id"),
            }
        )

    for row in pending.values():
        base_start = int(row["start_ms"])
        end_ms = _clamp_end(
            base_start,
            base_start + _UNCLOSED_TOOL_TAIL_MS,
            duration_ms,
        )
        spans.append(
            {
                "call_id": row.get("call_id"),
                "name": row.get("name") or "tool",
                "start_ms": base_start,
                "end_ms": end_ms,
                "duration_ms": None,
                "turn": row.get("turn"),
                "source": row.get("source"),
                "arguments": row.get("arguments"),
                "output": None,
                "is_error": False,
                "error": None,
                "parent_event_id": row.get("parent_event_id"),
            }
        )

    spans.sort(key=lambda s: (s["start_ms"], s["name"]))
    return spans


def _tool_spans_to_markers(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    for span in spans:
        is_error = bool(span.get("is_error"))
        mtype = MARKER_TOOL_ERROR if is_error else MARKER_TOOL
        name = str(span.get("name") or "tool")
        dur = span.get("duration_ms")
        detail_parts = [f"source={span.get('source') or '?'}", f"name={name}"]
        if dur is not None:
            detail_parts.append(f"duration={dur}ms")
        if span.get("error"):
            detail_parts.append(str(span["error"]))
        markers.append(
            {
                "type": mtype,
                "start_ms": int(span["start_ms"]),
                "end_ms": int(span["end_ms"]),
                "label": name,
                "detail": " · ".join(detail_parts),
                "tool_name": name,
                "is_error": is_error,
                "call_id": span.get("call_id"),
            }
        )
    return markers


def _build_session_summary(
    events: list[dict[str, Any]],
    t0: int,
    duration_ms: int | None,
) -> dict[str, Any] | None:
    usage: dict[str, Any] | None = None
    transitions: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for e in events:
        kind = str(e.get("kind") or "")
        if kind not in ("session.usage", "session.agent_state", "session.error"):
            continue
        try:
            mono = int(e.get("ts_mono_ms") or 0)
        except (TypeError, ValueError):
            continue
        at_ms = _mono_to_audio_ms(mono, t0, duration_ms)
        if at_ms is None:
            continue
        spec = e.get("spec") if isinstance(e.get("spec"), dict) else {}

        if kind == "session.usage":
            usage = dict(spec)
            continue

        if kind == "session.agent_state":
            old_state = spec.get("old_state")
            new_state = spec.get("new_state")
            if new_state is not None:
                transitions.append(
                    {
                        "at_ms": at_ms,
                        "from": str(old_state) if old_state is not None else None,
                        "to": str(new_state),
                    }
                )
            continue

        if kind == "session.error":
            msg = _spec_str(spec, "message", "error") or "session error"
            errors.append({"at_ms": at_ms, "message": msg})

    if usage is None and not transitions and not errors:
        return None

    out: dict[str, Any] = {}
    if usage is not None:
        out["usage"] = usage
    if transitions:
        out["state_transitions"] = transitions
    if errors:
        out["errors"] = errors
    return out


def _extract_chat_history(events: list[dict[str, Any]]) -> list[Any] | None:
    for e in reversed(events):
        if str(e.get("kind") or "") != "session.chat_history":
            continue
        spec = e.get("spec") if isinstance(e.get("spec"), dict) else {}
        items = spec.get("items")
        if isinstance(items, list):
            return items
    return None


def _build_tool_summary(
    spans: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, int]:
    tool_count = 0
    tool_errors = 0

    if isinstance(summary.get("tool_calls"), int):
        tool_count = int(summary["tool_calls"])
    elif isinstance(summary.get("metrics"), dict):
        metrics = summary["metrics"]
        if isinstance(metrics.get("tool_calls"), int):
            tool_count = int(metrics["tool_calls"])

    if isinstance(summary.get("tool_errors"), int):
        tool_errors = int(summary["tool_errors"])
    elif isinstance(summary.get("metrics"), dict):
        metrics = summary["metrics"]
        if isinstance(metrics.get("tool_errors"), int):
            tool_errors = int(metrics["tool_errors"])

    if tool_count <= 0:
        tool_count = len(spans)
    if tool_errors <= 0:
        tool_errors = sum(1 for s in spans if s.get("is_error"))

    return {"tool_count": tool_count, "tool_errors": tool_errors}
