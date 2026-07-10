"""In-process plugin registry for verify hooks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .api import SetupFn, VerifyPlugin

_verify: dict[str, VerifyPlugin] = {}
_setup_fns: list[SetupFn] = []
_loaded_keys: set[str] = set()


def register_verify(name: str, fn: VerifyPlugin) -> VerifyPlugin:
    """Register a verify plugin callable under a stable name (referenced from JSONL)."""
    key = name.strip()
    if not key:
        raise ValueError("verify plugin name must be non-empty")
    _verify[key] = fn
    return fn


def get_verify(name: str) -> VerifyPlugin | None:
    return _verify.get(name)


def list_verify_plugins() -> list[str]:
    return sorted(_verify.keys())


def register_setup(fn: SetupFn) -> SetupFn:
    """Optional one-shot setup when a plugin module loads."""
    _setup_fns.append(fn)
    return fn


def run_setup_hooks() -> None:
    for fn in _setup_fns:
        fn()


def mark_loaded(key: str) -> bool:
    """Return False if this load key was already processed."""
    if key in _loaded_keys:
        return False
    _loaded_keys.add(key)
    return True


def reset_for_tests() -> None:
    _verify.clear()
    _setup_fns.clear()
    _loaded_keys.clear()
