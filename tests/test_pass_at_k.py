"""Unit tests for pass@k flake control — validation logic only.

Full integration tests (LiveKit room) are skipped here; the flake loop
is tested via argument validation in ``execute_scenario``.
"""

import asyncio
import pytest
from pathlib import Path


def test_pass_at_k_reject_bad_args():
    """Validate the argument guards execute_scenario enforces (repeat < 1)."""
    from livekit_agent_simulator.ops import execute_scenario

    with pytest.raises(ValueError, match="repeat must be >= 1"):
        asyncio.run(execute_scenario("/tmp", "test", repeat=0))


def test_pass_at_k_reject_k_gt_n():
    from livekit_agent_simulator.ops import execute_scenario

    with pytest.raises(ValueError, match="pass_at_k"):
        asyncio.run(execute_scenario("/tmp", "test", repeat=3, pass_at_k=5))
