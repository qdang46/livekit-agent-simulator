"""Build time-aligned transcript cues + behavior markers for the report player."""

from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any


# Marker kinds exposed to the report player (stable API for the UI).
MARKER_BARGE_IN = "barge_in"
MARKER_SCRIPT_CUE = "script_cue"
MARKER_SILENCE_WAIT = "silence_wait"
MARKER_SILENCE = "silence"
MARKER_INTERRUPTION = "interruption"
MARKER_RECOVERY = "recovery"


def _wav_duration_ms(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate() or 1
            return int(frames * 1000 / rate)
    except Exception:
        return None


def _load_events(events_path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not events_path.exists():
        return events
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _resolve_audio_t0_ms(meta: dict[str, Any], events: list[dict[str, Any]]) -> int:
    audio = meta.get("audio") if isinstance(meta.get("audio"), dict) else {}
    if audio.get("t0_mono_ms") is not None:
        try:
            return max(0, int(audio["t0_mono_ms"]))
        except (TypeError, ValueError):
            pass
    # Fallback for older reports: first transcript-ish event.
    for e in events:
        kind = str(e.get("kind") or "")
        if kind.startswith("transcript.") or kind in (
            "sim.mic_published",
            "sim.gemini_connected",
        ):
            try:
                return max(0, int(e.get("ts_mono_ms") or 0))
            except (TypeError, ValueError):
                continue
    return 0


def _mono_to_audio_ms(mono: int, t0: int, duration_ms: int | None) -> int | None:
    start_ms = max(0, mono - t0)
    if duration_ms is not None and start_ms > duration_ms + 2000:
        return None
    return start_ms


def _clamp_end(start_ms: int, end_ms: int, duration_ms: int | None) -> int:
    end = max(start_ms + 120, end_ms)
    if duration_ms is not None:
        end = min(end, max(start_ms + 120, duration_ms))
    return end


def _collect_script_injects(
    events: list[dict[str, Any]],
    t0: int,
    duration_ms: int | None,
) -> list[dict[str, Any]]:
    """room_pcm / barge injects with real play duration (audio is heard immediately)."""
    out: list[dict[str, Any]] = []
    for e in events:
        if str(e.get("kind") or "") != "sim.script_inject":
            continue
        try:
            mono = int(e.get("ts_mono_ms") or 0)
        except (TypeError, ValueError):
            continue
        start = _mono_to_audio_ms(mono, t0, duration_ms)
        if start is None:
            continue
        spec = e.get("spec") if isinstance(e.get("spec"), dict) else {}
        try:
            dur = int(spec.get("duration_ms") or 0)
        except (TypeError, ValueError):
            dur = 0
        # gemini_text barge has no duration_ms — allow ~2s of audible speech
        if dur <= 0:
            delivery = str(spec.get("delivery") or "")
            dur = 2200 if delivery != "room_pcm" else 800
        out.append(
            {
                "start_ms": start,
                "duration_ms": dur,
                "end_ms": start + max(200, dur),
                "label": str(spec.get("label") or ""),
                "text": str(spec.get("text") or ""),
                "delivery": str(spec.get("delivery") or ""),
                "asset": spec.get("asset"),
            }
        )
    return out


def _inject_duration_near(
    injects: list[dict[str, Any]],
    at_ms: int,
    *,
    label: str = "",
    say: str = "",
) -> int | None:
    best: int | None = None
    best_d = 10_000
    for inj in injects:
        d = abs(int(inj["start_ms"]) - at_ms)
        if d > 900:
            continue
        # Prefer same label / text when available
        same = False
        if label and inj.get("label") and (
            label in str(inj["label"]) or str(inj["label"]) in label
        ):
            same = True
        if say and inj.get("text") and _text_overlap(say, str(inj["text"])):
            same = True
        score_d = d - (200 if same else 0)
        if score_d < best_d:
            best_d = score_d
            best = int(inj["duration_ms"])
    return best


def _build_markers(
    events: list[dict[str, Any]],
    t0: int,
    duration_ms: int | None,
) -> list[dict[str, Any]]:
    """Extract barge-in / silence / interruption / recovery markers aligned to audio."""
    markers: list[dict[str, Any]] = []
    barge_points: list[int] = []  # audio start_ms of barge-ins (for recovery)
    injects = _collect_script_injects(events, t0, duration_ms)

    for e in events:
        kind = str(e.get("kind") or "")
        try:
            mono = int(e.get("ts_mono_ms") or 0)
        except (TypeError, ValueError):
            continue
        start = _mono_to_audio_ms(mono, t0, duration_ms)
        if start is None:
            continue
        spec = e.get("spec") if isinstance(e.get("spec"), dict) else {}

        if kind == "sim.script.cue":
            barge = bool(spec.get("barge_in"))
            step_id = str(spec.get("step_id") or "")
            label = str(spec.get("label") or step_id or "script cue")
            say = str(spec.get("say") or "").strip()
            during = bool(spec.get("during_agent_speech"))
            waited = int(spec.get("waited_ms") or 0)
            mtype = MARKER_BARGE_IN if barge else MARKER_SCRIPT_CUE
            detail_parts = [
                f"trigger={spec.get('trigger') or '?'}",
                f"during_agent={during}",
            ]
            if say:
                detail_parts.append(f'say="{say}"')
            if waited:
                detail_parts.append(f"waited={waited}ms")
            # Prefer real inject play length so scrubber/highlight match audible audio.
            inj_dur = _inject_duration_near(injects, start, label=label, say=say)
            if barge:
                span = max(2200 if during else 1400, (inj_dur or 0) + 400)
            else:
                span = max(400, min(waited, 2000) or 400, (inj_dur or 0) + 200)
            end = _clamp_end(start, start + span, duration_ms)
            markers.append(
                {
                    "type": mtype,
                    "start_ms": start,
                    "end_ms": end,
                    "label": ("⚡ " if barge and during else "") + label,
                    "detail": " · ".join(detail_parts),
                    "step_id": step_id or None,
                    "say": say or None,
                    "during_agent_speech": during,
                    "barge_in": barge,
                    "audio_ms": inj_dur or span,
                }
            )
            if barge:
                barge_points.append(start)
            continue

        if kind == "sim.script.wait":
            step_id = str(spec.get("step_id") or "")
            label = str(spec.get("label") or step_id or "user pause")
            waited = int(spec.get("waited_ms") or 0)
            # Wait condition held for waited_ms ending at fire time.
            span = waited if waited > 0 else 1500
            win_start = max(0, start - span)
            end = _clamp_end(win_start, start + 200, duration_ms)
            markers.append(
                {
                    "type": MARKER_SILENCE_WAIT,
                    "start_ms": win_start,
                    "end_ms": end,
                    "label": label,
                    "detail": (
                        f"script wait · trigger={spec.get('trigger') or 'silence'} · "
                        f"held≈{span}ms"
                    ),
                    "step_id": step_id or None,
                    "trigger": spec.get("trigger"),
                }
            )
            continue

        if kind == "silence.detected":
            duration = int(spec.get("duration_ms") or 0)
            span = duration if duration > 0 else 4000
            win_start = max(0, start - span)
            end = _clamp_end(win_start, start, duration_ms)
            markers.append(
                {
                    "type": MARKER_SILENCE,
                    "start_ms": win_start,
                    "end_ms": end,
                    "label": "silence detected",
                    "detail": f"observer silence ≥ threshold ({span}ms)",
                    "duration_ms": span,
                }
            )
            continue

        if kind == "interruption":
            by = str(spec.get("by") or "unknown")
            note = str(spec.get("note") or "").strip()
            end = _clamp_end(start, start + 500, duration_ms)
            markers.append(
                {
                    "type": MARKER_INTERRUPTION,
                    "start_ms": start,
                    "end_ms": end,
                    "label": f"interruption ({by})",
                    "detail": note or f"by={by}",
                    "by": by,
                }
            )
            continue

    # Recovery: first agent final after each barge-in (agent spoke again).
    agent_finals: list[int] = []
    for e in events:
        kind = str(e.get("kind") or "")
        if kind != "transcript.agent.final":
            continue
        try:
            mono = int(e.get("ts_mono_ms") or 0)
        except (TypeError, ValueError):
            continue
        start = _mono_to_audio_ms(mono, t0, duration_ms)
        if start is None:
            continue
        agent_finals.append(start)

    used_agent: set[int] = set()
    for barge_ms in barge_points:
        recovery_ms = next((a for a in agent_finals if a > barge_ms and a not in used_agent), None)
        if recovery_ms is None:
            continue
        used_agent.add(recovery_ms)
        end = _clamp_end(recovery_ms, recovery_ms + 800, duration_ms)
        markers.append(
            {
                "type": MARKER_RECOVERY,
                "start_ms": recovery_ms,
                "end_ms": end,
                "label": "agent recovery",
                "detail": f"agent final after barge-in @ {barge_ms}ms",
                "after_barge_ms": barge_ms,
            }
        )

    markers.sort(key=lambda m: (m["start_ms"], m["type"]))
    return markers


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


def _norm_speech(s: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in s).split())


# Common particles / function words that must not alone prove script↔STT match.
_CONTENT_STOP = frozenset(
    {
        "được",
        "không",
        "mình",
        "bạn",
        "với",
        "cho",
        "của",
        "này",
        "đó",
        "là",
        "và",
        "các",
        "một",
        "như",
        "để",
        "có",
        "thì",
        "rồi",
        "nữa",
        "when",
        "what",
        "that",
        "this",
        "with",
        "have",
        "from",
        "your",
        "will",
        "been",
        "were",
        "they",
        "them",
        "than",
        "then",
        "also",
        "just",
        "into",
        "over",
        "more",
        "hook",  # alone too weak without "khoan"
    }
)


def _text_overlap(a: str, b: str) -> bool:
    """Match script say ↔ STT without false positives on common particles.

    Prefer phrase substring; else require distinctive content words (not
    particles like được/không that appear in almost every VI turn).
    """
    na, nb = _norm_speech(a), _norm_speech(b)
    if not na or not nb:
        return False
    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(shorter) >= 5 and shorter in longer:
        return True
    # Prefer matching against the shorter side as the "script say" fingerprint.
    wa = {w for w in na.split() if len(w) >= 4 and w not in _CONTENT_STOP}
    wb = {w for w in nb.split() if len(w) >= 4 and w not in _CONTENT_STOP}
    inter = wa & wb
    if not inter:
        return False
    if any(len(w) >= 5 for w in inter):
        return True
    return len(inter) >= 2


def _pin_script_window(
    c: dict[str, Any],
    matched: dict[str, Any],
    *,
    origin: str,
    final_ms: int,
) -> None:
    if matched.get("step_id"):
        c["script_step_id"] = matched.get("step_id")
    if matched.get("say"):
        c["script_say"] = matched.get("say")
    if matched.get("label"):
        c["script_label"] = matched.get("label")
    inject_ms = int(matched.get("start_ms") or final_ms)
    try:
        audio_ms = int(matched.get("audio_ms") or 0)
    except (TypeError, ValueError):
        audio_ms = 0
    if audio_ms <= 0:
        audio_ms = 2200 if origin == "script_barge" else 900
    c["start_ms"] = max(0, inject_ms - 80)
    c["end_ms"] = max(
        final_ms + 500,
        inject_ms + audio_ms + 350,
        int(c.get("end_ms") or 0),
    )
    c["inject_ms"] = inject_ms


def _tag_cues_with_markers(
    cues: list[dict[str, Any]], markers: list[dict[str, Any]]
) -> None:
    """Attach nearby marker types + classify script barge speech vs natural caller."""
    barge_markers = [
        m
        for m in markers
        if m.get("type") == MARKER_BARGE_IN or m.get("barge_in")
    ]
    script_markers = [
        m for m in markers if m.get("type") in (MARKER_BARGE_IN, MARKER_SCRIPT_CUE)
    ]

    for c in cues:
        tags: list[str] = []
        start = int(c["start_ms"])
        end = int(c.get("end_ms") or start)
        final_ms = int(c.get("final_ms") if c.get("final_ms") is not None else end)
        for m in markers:
            mtype = str(m["type"])
            ms = int(m["start_ms"])
            me = int(m.get("end_ms") or ms)
            near = (
                abs(ms - final_ms) <= 8000
                or abs(ms - start) <= 1200
                or (ms <= end and me >= start)
            )
            if not near:
                continue
            if mtype not in tags:
                tags.append(mtype)
        if tags:
            c["marker_tags"] = tags

        # User channel audio that is really a Script barge/inject — not persona chat.
        if str(c.get("role")) != "user":
            c["speech_origin"] = "natural"
            continue

        text = str(c.get("text") or "")
        origin = "natural"
        matched: dict[str, Any] | None = None
        best_score = -1

        for m in script_markers:
            ms = int(m["start_ms"])
            say = str(m.get("say") or "")
            is_barge = bool(m.get("barge_in") or m.get("type") == MARKER_BARGE_IN)
            # STT often lags inject by several seconds (especially LiveKit STT).
            delta = final_ms - ms  # >0 ⇒ transcript after inject
            if delta < -800 or delta > 15000:
                continue
            text_hit = (
                _text_overlap(text, say)
                if say and not str(say).startswith("[")
                else False
            )
            # Without text match: only ultra-short STT near inject ("khoan đã", "uh-huh").
            word_n = len(text.split())
            tiny = word_n <= 3 and len(text.strip()) <= 28
            if is_barge:
                if text_hit and -500 <= delta <= 15000:
                    accept = True
                    score = 100 - min(40, max(0, delta) // 400)
                elif tiny and 0 <= delta <= 3500:
                    accept = True
                    score = 70 - min(30, delta // 200)
                else:
                    accept = False
                    score = 0
            else:
                accept = text_hit and 0 <= delta <= 8000
                score = 50 if accept else 0
            if accept and score > best_score:
                best_score = score
                matched = m
                origin = "script_barge" if is_barge else "script_cue"

        # Time-only fallback: 1–2 word STT near inject.
        if origin == "natural" and len(text.split()) <= 2 and len(text.strip()) <= 24:
            for m in barge_markers:
                ms = int(m["start_ms"])
                delta = final_ms - ms
                if 0 <= delta <= 3500:
                    matched = m
                    origin = "script_barge"
                    break

        # Late STT of barge text (e.g. "khoan đã" many seconds after inject):
        # score by phrase quality first, then time closeness.
        if origin == "natural" and len(text.split()) <= 4:
            best_m = None
            best_key: tuple[int, int] | None = None
            nt = _norm_speech(text)
            for m in barge_markers:
                say = str(m.get("say") or "")
                if not say or str(say).startswith("["):
                    continue
                if not _text_overlap(text, say):
                    continue
                ms = int(m["start_ms"])
                delta = final_ms - ms
                if delta < -500:
                    continue
                ns = _norm_speech(say)
                # Prefer full phrase containment (khoan đã ⊂ cut-in-1 say)
                phrase = 2 if nt and ns and (nt in ns or ns in nt) else 1
                # Higher phrase, then closer in time
                key = (phrase, -abs(delta))
                if best_key is None or key > best_key:
                    best_key = key
                    best_m = m
            if best_m is not None:
                matched = best_m
                origin = "script_barge"

        c["speech_origin"] = origin
        if matched is not None:
            _pin_script_window(c, matched, origin=origin, final_ms=final_ms)
            # Prefer full script line on the card; keep STT fragment for detail.
            say = str(matched.get("say") or "").strip()
            if (
                say
                and not say.startswith("[")
                and len(text.strip()) < len(say)
                and len(text.split()) <= 6
            ):
                c["stt_text"] = text
                c["text"] = say


def _synthetic_script_barge_cues(
    markers: list[dict[str, Any]],
    existing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Always show a center-column card at inject time — do not rely on laggy STT.

    Real runs often never get a clean user.final for gemini_text barge, or STT
    arrives many seconds later and looks like natural Caller speech.
    """
    covered_steps: set[str] = set()
    covered_injects: list[int] = []
    for c in existing:
        if c.get("speech_origin") not in ("script_barge", "script_cue"):
            continue
        sid = c.get("script_step_id")
        if sid:
            covered_steps.add(str(sid))
        if c.get("inject_ms") is not None:
            try:
                covered_injects.append(int(c["inject_ms"]))
            except (TypeError, ValueError):
                pass

    out: list[dict[str, Any]] = []
    for m in markers:
        if not (m.get("barge_in") or m.get("type") == MARKER_BARGE_IN):
            continue
        step_id = str(m.get("step_id") or "")
        inject_ms = int(m.get("start_ms") or 0)
        if step_id and step_id in covered_steps:
            continue
        if any(abs(inject_ms - t) < 600 for t in covered_injects):
            continue
        say = str(m.get("say") or "").strip()
        label = str(m.get("label") or step_id or "script barge").strip()
        # Prefer human script text; bracket placeholders → use label
        display = say if say and not (say.startswith("[") and say.endswith("]")) else label
        if display.startswith("⚡"):
            display = display.lstrip("⚡ ").strip()
        try:
            audio_ms = int(m.get("audio_ms") or 0)
        except (TypeError, ValueError):
            audio_ms = 0
        if audio_ms <= 0:
            audio_ms = max(1200, int(m.get("end_ms") or inject_ms) - inject_ms)
        end_ms = max(inject_ms + audio_ms + 350, inject_ms + 1200)
        out.append(
            {
                "role": "user",
                "start_ms": max(0, inject_ms - 80),
                "end_ms": end_ms,
                "final_ms": end_ms,
                "text": display,
                "speech_origin": "script_barge",
                "script_step_id": step_id or None,
                "script_say": say or display,
                "script_label": label,
                "inject_ms": inject_ms,
                "synthetic": True,
                "source": "sim.script",
                "marker_tags": [MARKER_BARGE_IN],
            }
        )
        if step_id:
            covered_steps.add(step_id)
        covered_injects.append(inject_ms)
    return out


def build_cues_payload(report_dir: Path) -> dict[str, Any]:
    """Return cues.json body for a single run report directory."""
    report_dir = Path(report_dir)
    run_id = report_dir.name
    events = _load_events(report_dir / "events.jsonl")
    meta = _load_json(report_dir / "meta.json")
    summary = _load_json(report_dir / "summary.json")

    wav_path = report_dir / "conversation.wav"
    duration_ms = _wav_duration_ms(wav_path)
    audio_meta = meta.get("audio") if isinstance(meta.get("audio"), dict) else {}
    if duration_ms is None and audio_meta.get("duration_ms") is not None:
        try:
            duration_ms = int(audio_meta["duration_ms"])
        except (TypeError, ValueError):
            duration_ms = None

    t0 = _resolve_audio_t0_ms(meta, events)
    cues = _build_transcript_cues(events, t0, duration_ms)
    markers = _build_markers(events, t0, duration_ms)
    _tag_cues_with_markers(cues, markers)
    # Guarantee inject-time cards even when STT misses or mis-attributes barge speech.
    cues.extend(_synthetic_script_barge_cues(markers, cues))

    script_verify = summary.get("script_verify") if isinstance(summary, dict) else None
    assert_verify = summary.get("assert_verify") if isinstance(summary, dict) else None
    if not isinstance(script_verify, dict):
        # Fallback: last script.verify event
        for e in reversed(events):
            if e.get("kind") == "script.verify" and isinstance(e.get("spec"), dict):
                script_verify = e["spec"]
                break
    if not isinstance(assert_verify, dict):
        for e in reversed(events):
            if e.get("kind") == "assert.verify" and isinstance(e.get("spec"), dict):
                assert_verify = e["spec"]
                break

    caller = summary.get("caller") if isinstance(summary, dict) else None
    behavior_summary = None
    if isinstance(caller, dict) and isinstance(caller.get("behavior_summary"), dict):
        behavior_summary = caller["behavior_summary"]
    elif isinstance(summary, dict) and isinstance(summary.get("behavior_summary"), dict):
        behavior_summary = summary["behavior_summary"]
    if behavior_summary is None and events:
        # Older reports / live API without summary field — recompute from events.
        from ..script_runner import build_caller_behavior_summary

        behavior_summary = build_caller_behavior_summary(events)

    counts: dict[str, int] = {}
    for m in markers:
        t = str(m["type"])
        counts[t] = counts.get(t, 0) + 1

    return {
        "run_id": run_id,
        "scenario_id": meta.get("scenario_id") or summary.get("scenario_id"),
        "audio": {
            "file": "conversation.wav" if wav_path.exists() else None,
            "duration_ms": duration_ms,
            "t0_mono_ms": t0,
            "channels": audio_meta.get("channels") or {"left": "sim", "right": "agent"},
        },
        "cues": cues,
        "markers": markers,
        "marker_counts": counts,
        "script_verify": script_verify,
        "assert_verify": assert_verify,
        "caller": {"behavior_summary": behavior_summary} if behavior_summary is not None else None,
        "behavior_summary": behavior_summary,
    }


def write_cues_json(report_dir: Path) -> Path:
    """Write ``cues.json`` into the report dir; return path."""
    report_dir = Path(report_dir)
    payload = build_cues_payload(report_dir)
    out = report_dir / "cues.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
