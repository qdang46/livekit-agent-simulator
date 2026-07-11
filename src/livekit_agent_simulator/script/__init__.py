"""Script domain: timed caller cues, runtime runner, log verify, behavior summary.

Public re-exports (prefer importing from here or legacy ``script_runner``):
  ScriptStep, ScriptVerifySpec, ScriptRunner, SUPPORTED_*, evaluate_script_log,
  build_caller_behavior_summary
"""

from __future__ import annotations

from .models import SUPPORTED_ACTIONS, SUPPORTED_TRIGGERS, ScriptStep, ScriptVerifySpec
from .runtime import ScriptRunner
from .summary import build_caller_behavior_summary
from .verify import evaluate_script_log

__all__ = [
    "SUPPORTED_ACTIONS",
    "SUPPORTED_TRIGGERS",
    "ScriptStep",
    "ScriptVerifySpec",
    "ScriptRunner",
    "build_caller_behavior_summary",
    "evaluate_script_log",
]
