"""Load and validate `.agent-sim/config.yaml`.

POC contract (see plan): credentials are written directly in the file; the whole
`.agent-sim/` folder is gitignored. No env-var substitution in v1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DOT_FOLDER = ".agent-sim"
CONFIG_FILENAME = "config.yaml"


class ConfigError(Exception):
    """Raised when config.yaml is missing or invalid. Message is user-actionable."""


@dataclass
class LiveKitConfig:
    url: str
    api_key: str
    api_secret: str
    agent_name: str
    room_prepare_ms: int = 500
    agent_join_timeout_ms: int = 25_000
    dispatch_metadata: str | None = None


@dataclass
class SimulatorVoiceConfig:
    mode: str = "realtime"
    provider: str = "google"
    model: str = "gemini-3.1-flash-live-preview"
    voice: str = "Puck"
    language: str = "ja-JP"


@dataclass
class SimulatorConfig:
    google_api_key: str
    provider: str = "google"
    model: str = "gemini-2.5-flash"
    temperature: float = 0.7
    language: str = "ja-JP"
    voice: SimulatorVoiceConfig = field(default_factory=SimulatorVoiceConfig)


@dataclass
class JudgeConfig:
    provider: str = "google"
    model: str = "gemini-2.5-flash"
    temperature: float = 0.0


@dataclass
class ToolEventPattern:
    match: dict[str, Any]
    emit: str  # tool.start | tool.end | tool.error


@dataclass
class ObserveConfig:
    timezone: str = "Asia/Ho_Chi_Minh"
    lk_transcription: bool = True
    save_audio_segments: bool = False
    export_turn_snapshots: bool = False
    data_topics: list[str] = field(default_factory=list)
    tool_event_patterns: list[ToolEventPattern] = field(default_factory=list)
    # Payload `type` values treated as transcript turns on any subscribed data topic.
    transcript_payload_types: list[str] = field(default_factory=lambda: ["transcript_turn"])
    transcript_dedupe_window_ms: int = 15_000
    silence_threshold_ms: int = 4_000
    turn_taking_warn_ms: int = 2_500


@dataclass
class SimConfig:
    project_root: Path
    livekit: LiveKitConfig
    simulator: SimulatorConfig
    observe: ObserveConfig = field(default_factory=ObserveConfig)
    judge: JudgeConfig | None = None
    project: str | None = None

    @property
    def dot_dir(self) -> Path:
        return self.project_root / DOT_FOLDER

    @property
    def reports_dir(self) -> Path:
        return self.dot_dir / "reports"

    @property
    def scenarios_dir(self) -> Path:
        return self.dot_dir / "scenarios"

    @property
    def sqlite_path(self) -> Path:
        return self.dot_dir / "runs.sqlite"


def _require(section: dict[str, Any], key: str, section_name: str) -> Any:
    value = section.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ConfigError(
            f"Missing `{section_name}.{key}` in {DOT_FOLDER}/{CONFIG_FILENAME}. "
            f"Copy the value from LiveKit Cloud / your worker and try again."
        )
    return value


def load_config(project_root: Path | str) -> SimConfig:
    project_root = Path(project_root).resolve()
    config_path = project_root / DOT_FOLDER / CONFIG_FILENAME
    if not config_path.exists():
        raise ConfigError(
            f"{config_path} not found. Run `lk-sim init` (or the `init_project` MCP tool) "
            f"to scaffold {DOT_FOLDER}/ first."
        )

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"{config_path} is not valid YAML: {e}") from e
    if not isinstance(raw, dict):
        raise ConfigError(f"{config_path} must be a YAML mapping at the top level.")

    lk_raw = raw.get("livekit")
    if not isinstance(lk_raw, dict):
        raise ConfigError(f"Missing `livekit:` section in {config_path}.")
    dispatch_metadata = lk_raw.get("dispatch_metadata")
    if dispatch_metadata is not None:
        dispatch_metadata = str(dispatch_metadata).strip() or None

    livekit = LiveKitConfig(
        url=str(_require(lk_raw, "url", "livekit")),
        api_key=str(_require(lk_raw, "api_key", "livekit")),
        api_secret=str(_require(lk_raw, "api_secret", "livekit")),
        agent_name=str(_require(lk_raw, "agent_name", "livekit")),
        room_prepare_ms=int(lk_raw.get("room_prepare_ms", 500)),
        agent_join_timeout_ms=int(lk_raw.get("agent_join_timeout_ms", 25_000)),
        dispatch_metadata=dispatch_metadata,
    )

    sim_raw = raw.get("simulator")
    if not isinstance(sim_raw, dict):
        raise ConfigError(f"Missing `simulator:` section in {config_path}.")
    voice_raw = sim_raw.get("voice") or {}
    voice = SimulatorVoiceConfig(
        mode=str(voice_raw.get("mode", "realtime")),
        provider=str(voice_raw.get("provider", "google")),
        model=str(voice_raw.get("model", "gemini-3.1-flash-live-preview")),
        voice=str(voice_raw.get("voice", "Puck")),
        language=str(voice_raw.get("language", sim_raw.get("language", "ja-JP"))),
    )
    simulator = SimulatorConfig(
        google_api_key=str(_require(sim_raw, "google_api_key", "simulator")),
        provider=str(sim_raw.get("provider", "google")),
        model=str(sim_raw.get("model", "gemini-2.5-flash")),
        temperature=float(sim_raw.get("temperature", 0.7)),
        language=str(sim_raw.get("language", "ja-JP")),
        voice=voice,
    )

    judge: JudgeConfig | None = None
    judge_raw = raw.get("judge")
    if isinstance(judge_raw, dict):
        judge = JudgeConfig(
            provider=str(judge_raw.get("provider", "google")),
            model=str(judge_raw.get("model", "gemini-2.5-flash")),
            temperature=float(judge_raw.get("temperature", 0.0)),
        )

    obs_raw = raw.get("observe") or {}
    patterns: list[ToolEventPattern] = []
    for p in obs_raw.get("tool_event_patterns") or []:
        if isinstance(p, dict) and isinstance(p.get("match"), dict) and p.get("emit"):
            patterns.append(ToolEventPattern(match=p["match"], emit=str(p["emit"])))
    observe = ObserveConfig(
        timezone=str(obs_raw.get("timezone", "Asia/Ho_Chi_Minh")),
        lk_transcription=bool(obs_raw.get("lk_transcription", True)),
        save_audio_segments=bool(obs_raw.get("save_audio_segments", False)),
        export_turn_snapshots=bool(obs_raw.get("export_turn_snapshots", False)),
        data_topics=[str(t) for t in (obs_raw.get("data_topics") or [])],
        tool_event_patterns=patterns,
        transcript_payload_types=[
            str(t) for t in (obs_raw.get("transcript_payload_types") or ["transcript_turn"])
        ],
        transcript_dedupe_window_ms=int(obs_raw.get("transcript_dedupe_window_ms", 15_000)),
        silence_threshold_ms=int(obs_raw.get("silence_threshold_ms", 4_000)),
        turn_taking_warn_ms=int(obs_raw.get("turn_taking_warn_ms", 2_500)),
    )

    return SimConfig(
        project_root=project_root,
        livekit=livekit,
        simulator=simulator,
        observe=observe,
        judge=judge,
        project=raw.get("project"),
    )


def config_snapshot(cfg: SimConfig) -> dict[str, Any]:
    """Redacted config for `run.started.config_snapshot` — never includes secrets."""
    gaps: list[str] = []
    if not cfg.observe.tool_event_patterns:
        gaps.append("tool_events")
    return {
        "project": cfg.project,
        "livekit": {
            "url_host": cfg.livekit.url.split("://")[-1].split("/")[0],
            "agent_name": cfg.livekit.agent_name,
            "agent_join_timeout_ms": cfg.livekit.agent_join_timeout_ms,
            "dispatch_metadata_set": bool(cfg.livekit.dispatch_metadata),
        },
        "simulator": {
            "voice_model": cfg.simulator.voice.model,
            "voice": cfg.simulator.voice.voice,
            "language": cfg.simulator.voice.language,
        },
        "judge_enabled": cfg.judge is not None,
        "observe": {
            "lk_transcription": cfg.observe.lk_transcription,
            "data_topics": cfg.observe.data_topics,
            "silence_threshold_ms": cfg.observe.silence_threshold_ms,
        },
        "observe_gaps": gaps,
    }
