"""Public Python API for livekit-agent-simulator."""

from __future__ import annotations

__version__ = "0.1.0"

from . import ops
from .config import ConfigError, SimConfig, load_config
from .plugins import (
    VerifyContext,
    ensure_plugins_loaded,
    get_verify,
    list_verify_plugins,
    register_setup,
    register_verify,
    verify_plugin,
)
from .scenario import Scenario, ScenarioError, parse_scenario
from .scenario_from_dict import export_scenario_dict, scenario_from_dict
from .script import ScriptStep, ScriptVerifySpec, evaluate_script_log

__all__ = [
    "__version__",
    "ConfigError",
    "Scenario",
    "ScenarioError",
    "ScriptStep",
    "ScriptVerifySpec",
    "SimConfig",
    "VerifyContext",
    "ensure_plugins_loaded",
    "evaluate_script_log",
    "export_scenario_dict",
    "get_verify",
    "list_verify_plugins",
    "load_config",
    "ops",
    "parse_scenario",
    "register_setup",
    "register_verify",
    "scenario_from_dict",
    "verify_plugin",
]
