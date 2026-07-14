"""Factory: Caller.mode → SimLeg strategy."""

from __future__ import annotations

from .agent_dials import AgentDialsSimLeg
from .human_pickup import OutboundHumanPickupSimLeg
from .inbound import InboundSipSimLeg
from .protocol import SimLeg, SimLegError
from .sim_callee import OutboundSimCalleeSimLeg
from .webrtc import WebRtcSimLeg


def sim_leg_factory(mode: str) -> SimLeg:
    """Map ``Caller.mode`` → strategy instance."""
    m = (mode or "webrtc_sim").strip().lower()
    if m == "webrtc_sim":
        return WebRtcSimLeg()
    if m == "outbound_human_pickup":
        return OutboundHumanPickupSimLeg()
    if m == "outbound_sim_callee":
        return OutboundSimCalleeSimLeg()
    if m == "inbound_sip":
        return InboundSipSimLeg()
    if m == "agent_dials":
        return AgentDialsSimLeg()
    raise SimLegError(
        f"Unknown Caller.mode {mode!r}. "
        f"Expected webrtc_sim | inbound_sip | outbound_human_pickup | "
        f"outbound_sim_callee | agent_dials."
    )
