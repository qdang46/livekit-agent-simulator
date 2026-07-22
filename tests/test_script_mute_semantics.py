"""Post-cue mute: wait holds silence; speak/line must not long-mute freestyle."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest

from livekit_agent_simulator.script.models import ScriptStep
from livekit_agent_simulator.script.runtime import ScriptRunner


class _FakeBridge:
    def __init__(self) -> None:
        self.suppress_calls: list[int] = []
        self.silence_calls: list[int] = []
        self.injected: list[str] = []
        self.end_call = asyncio.Event()

    def suppress_persona_output(self, duration_ms: int) -> None:
        self.suppress_calls.append(int(duration_ms))

    def begin_scripted_user_silence(self, duration_ms: int, *, grace_s: float = 20.0) -> None:
        self.silence_calls.append(int(duration_ms))
        self.suppress_persona_output(duration_ms)

    async def inject_cue(self, text: str, **kwargs: Any) -> None:
        self.injected.append(str(text))

    def sim_hang_up(self) -> None:
        self.end_call.set()


def _runner(steps: list[ScriptStep], bridge: _FakeBridge) -> ScriptRunner:
    observer = MagicMock()
    observer.agent_is_active_speaker = False
    observer.agent_has_spoken = True
    observer.agent_active_duration_ms.return_value = 0
    writer = MagicMock()
    return ScriptRunner(steps, observer, bridge, writer)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_speak_line_does_not_suppress_for_silence_after_cue_ms() -> None:
    """silence_after_cue_ms on speak is not a freestyle blackout (inject drains TTS)."""
    bridge = _FakeBridge()
    step = ScriptStep(
        id="open",
        trigger="silence",
        delay_ms=0,
        say="Hello, my name is Mai",
        action="speak",
        silence_after_cue_ms=45_000,
    )
    runner = _runner([step], bridge)
    await runner._fire(step, waited_ms=0)
    assert bridge.injected == ["Hello, my name is Mai"]
    assert bridge.suppress_calls == []
    assert bridge.silence_calls == []


@pytest.mark.asyncio
async def test_wait_still_holds_intentional_silence() -> None:
    bridge = _FakeBridge()
    step = ScriptStep(
        id="quiet",
        trigger="silence",
        delay_ms=0,
        action="wait",
        silence_after_cue_ms=50,
    )
    runner = _runner([step], bridge)
    await runner._fire(step, waited_ms=0)
    assert bridge.silence_calls == [50]
    assert bridge.suppress_calls == [50]
    assert bridge.injected == []
