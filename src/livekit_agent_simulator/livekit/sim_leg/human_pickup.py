"""Outbound human-pickup SimLeg — human answers; Gemini speaks in the same agent room."""

from __future__ import annotations

import asyncio
import time

from ..adapter import SIM_IDENTITY
from .errors import sip_error_spec
from .protocol import SimLegContext, SimLegError, SimLegHandle

MODE = "outbound_human_pickup"


class OutboundHumanPickupSimLeg:
    """Dial a human/PSTN number into agent-room; after answer, Gemini WebRTC speaks there.

    Handset isolation (default ``mute_and_unsubscribe``) reduces human ↔ room audio so
    Gemini replaces the talker. No sim DID / second room required. Manual / attended tests —
    use ``outbound_sim_callee`` for automated Gemini-as-SIP-callee.
    """

    async def connect(self, ctx: SimLegContext) -> SimLegHandle:
        from ...scenario import effective_telephony

        tel = effective_telephony(ctx.scenario, ctx.cfg)
        if not tel.outbound_trunk_id:
            raise SimLegError(
                f"{MODE} requires telephony.outbound_trunk_id "
                "(config) or Telephony.sip_trunk_id (scenario)."
            )
        if not tel.call_to:
            raise SimLegError(
                f"{MODE} requires Telephony.call_to "
                "(human/PSTN number that will answer — not sim DID)."
            )

        adapter, writer = ctx.adapter, ctx.writer

        dispatch = await adapter.create_room_and_dispatch(ctx.run_id, ctx.dispatch_metadata)
        agent_room_name = dispatch.room_name
        writer.emit(
            "dispatch.created",
            spec={
                "room": agent_room_name,
                "agent_name": ctx.cfg.livekit.agent_name,
                "mode": MODE,
                "dispatch_id": dispatch.dispatch_id,
                "metadata_set": bool(ctx.dispatch_metadata),
            },
            include_dialogue=False,
        )

        agent_identity = await adapter.wait_for_agent(agent_room_name)
        writer.emit(
            "dispatch.agent_joined",
            spec={
                "identity": agent_identity,
                "mode": MODE,
                "dispatch_id": dispatch.dispatch_id,
            },
            include_dialogue=False,
        )

        prepare_ms = tel.prepare_ms
        if prepare_ms > 0:
            writer.emit(
                "outbound.prepare",
                spec={"prepare_ms": prepare_ms, "mode": MODE},
                include_dialogue=False,
            )
            await asyncio.sleep(prepare_ms / 1000)

        sip_identity = f"sip-out-{ctx.run_id[:12]}"
        writer.emit(
            "outbound.dial_started",
            spec={
                "call_to": tel.call_to,
                "trunk_id_set": True,
                "room": agent_room_name,
                "participant_identity": sip_identity,
                "wait_until_answered": tel.wait_until_answered,
                "mode": MODE,
            },
            include_dialogue=False,
        )
        t0 = time.monotonic()
        try:
            sip_info = await adapter.create_sip_participant(
                room_name=agent_room_name,
                sip_trunk_id=tel.outbound_trunk_id,
                sip_call_to=tel.call_to,
                participant_identity=sip_identity,
                participant_name="Human Handset",
                wait_until_answered=tel.wait_until_answered,
                krisp_enabled=tel.krisp_enabled,
            )
        except Exception as e:
            writer.emit(
                "outbound.dial_failed",
                spec=sip_error_spec(e, call_to=tel.call_to),
                include_dialogue=False,
            )
            raise SimLegError(f"outbound_human_pickup dial failed: {e}") from e

        dial_ms = int((time.monotonic() - t0) * 1000)
        sip_part_id = getattr(sip_info, "participant_identity", None) or sip_identity
        writer.emit(
            "outbound.dial_answered",
            spec={
                "call_to": tel.call_to,
                "dial_ms": dial_ms,
                "participant_identity": sip_part_id,
                "sip_call_id": getattr(sip_info, "sip_call_id", None),
                "mode": MODE,
            },
            include_dialogue=False,
        )
        writer.emit(
            "sip.participant_connected",
            spec={
                "identity": sip_part_id,
                "room": agent_room_name,
                "role": "human_handset",
            },
            include_dialogue=False,
        )

        # Gemini joins the same room as agent (WebRTC topology after PSTN answer).
        room = await adapter.connect_simulator(agent_room_name)
        writer.emit(
            "sim.connected",
            spec={
                "identity": SIM_IDENTITY,
                "room": agent_room_name,
                "mode": MODE,
                "note": "Gemini colocated with agent after human answer",
            },
            include_dialogue=False,
        )

        isolation = tel.handset_isolation
        iso_result = await adapter.isolate_sip_handset(
            room_name=agent_room_name,
            sip_identity=sip_part_id,
            isolation=isolation,
        )
        writer.emit(
            "outbound.handset_isolated",
            spec={
                "sip_identity": sip_part_id,
                **iso_result,
            },
            include_dialogue=False,
        )

        return SimLegHandle(
            agent_room=room,
            sim_room=room,
            agent_room_name=agent_room_name,
            sim_room_name=agent_room_name,
            sim_identity=SIM_IDENTITY,
            agent_identity=agent_identity,
            mode=MODE,
            gemini_listen_identity=agent_identity,
            gemini_listen_sip=False,
            gemini_listen_agent_room=False,
            rooms_to_delete=[agent_room_name],
            meta={
                "dial_ms": dial_ms,
                "call_to": tel.call_to,
                "sip_identity": sip_part_id,
                "sip_call_id": getattr(sip_info, "sip_call_id", None),
                "dispatch_id": dispatch.dispatch_id,
                "handset_isolation": isolation,
                "isolation": iso_result,
            },
        )
