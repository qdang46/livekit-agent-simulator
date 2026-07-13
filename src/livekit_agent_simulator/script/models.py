"""Script step / verify models (pure data, no I/O)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SUPPORTED_TRIGGERS = frozenset({"agent_speaking", "silence", "time"})
SUPPORTED_ACTIONS = frozenset({"speak", "wait", "hang_up"})


@dataclass(frozen=True)
class ScriptStep:
    id: str
    trigger: str
    delay_ms: int
    say: str = ""
    label: str = ""
    once: bool = True
    min_agent_active_ms: int = 400
    delivery: str = "gemini_text"  # gemini_text | room_pcm
    asset: str | None = None
    silence_after_cue_ms: int = 0
    action: str = "speak"  # speak | wait | hang_up
    # For silence trigger: only start counting idle after agent has spoken once.
    require_agent_spoke_first: bool = True
    barge_in: bool = False
    # When barge_in + gemini_text: play builtin noise.blip first (audible cut-in).
    with_blip: bool = True
    # Linear playback gain for this cue (0.0–1.0). Applies to gemini_text TTS and room_pcm.
    gain: float = 1.0


@dataclass(frozen=True)
class ScriptVerifySpec:
    require_during_agent_speech: bool = True
    min_agent_finals_after_first_cue: int = 0
    min_user_finals_after_first_cue: int = 0
    min_interruptions: int | None = None
    max_interruptions: int | None = None
    # After a silence-wait step, require agent transcript final later (agent re-prompts).
    min_agent_finals_after_silence: int = 0
    # After a barge_in cue, require agent to speak again (recovery).
    min_agent_finals_after_barge_in: int = 0
    plugins: tuple[str, ...] = ()
    plugin_options: dict[str, Any] = field(default_factory=dict)


