"""Transcript finals → playback cue ranges for the report player."""

from __future__ import annotations

from typing import Any

from .report_time import _mono_to_audio_ms

def _build_transcript_cues(
    events: list[dict[str, Any]],
    t0: int,
    duration_ms: int | None,
) -> list[dict[str, Any]]:
    raw: list[dict[str, Any]] = []
    for e in events:
        kind = str(e.get("kind") or "")
        if not kind.startswith("transcript.") or not kind.endswith(".final"):
            continue
        spec = e.get("spec") or {}
        text = (spec.get("text") or "").strip()
        if not text:
            continue
        if "agent" in kind:
            role = "agent"
        elif "user" in kind:
            role = "user"
        else:
            continue
        try:
            mono = int(e.get("ts_mono_ms") or 0)
        except (TypeError, ValueError):
            continue
        start_ms = _mono_to_audio_ms(mono, t0, duration_ms)
        if start_ms is None:
            continue
        raw.append(
            {
                "role": role,
                "start_ms": start_ms,
                "text": text,
                "turn": e.get("turn"),
                "source": e.get("source"),
                "kind": kind,
                "ts_mono_ms": mono,
            }
        )

    # Prefer higher-quality sources if duplicates at same role+approx time
    raw.sort(key=lambda c: (c["start_ms"], 0 if c["role"] == "agent" else 1))
    cues: list[dict[str, Any]] = []
    for c in raw:
        if cues:
            prev = cues[-1]
            if (
                prev["role"] == c["role"]
                and abs(prev["start_ms"] - c["start_ms"]) < 800
                and (prev["text"] in c["text"] or c["text"] in prev["text"])
            ):
                # Keep longer text
                if len(c["text"]) > len(prev["text"]):
                    cues[-1] = c
                continue
        cues.append(c)

    # Event timestamps are *final* (end of speech). Map ranges so playback
    # highlight covers the utterance window, not only the post-final gap:
    #   start ≈ previous final (or 0), end ≈ this final.
    finals = [int(c["start_ms"]) for c in cues]
    for i, c in enumerate(cues):
        final_ms = finals[i]
        c["final_ms"] = final_ms
        if i == 0:
            start = 0
        else:
            start = finals[i - 1]
        # Keep a small tail so the last word stays highlighted briefly.
        if i + 1 < len(cues):
            tail = min(600, max(0, finals[i + 1] - final_ms) // 2)
        elif duration_ms is not None:
            tail = min(800, max(0, int(duration_ms) - final_ms))
        else:
            tail = 600
        end = final_ms + tail
        c["start_ms"] = start
        c["end_ms"] = max(start + 200, end)

    return cues


