"""LLM judge — text-only Gemini scoring of the finished run against PassCriteria."""

from __future__ import annotations

import json
from typing import Any

from google import genai
from google.genai import types

from ..config import JudgeConfig

JUDGE_SYSTEM = """You are a strict QA judge for voice-agent test calls.
You receive: (1) the pass criteria, (2) the conversation transcript per turn,
(3) tool call spans with errors. Evaluate ONLY against the criteria.
Return JSON: {"verdict": "pass"|"fail", "score": 0-100,
"criteria": [{"criterion": str, "met": bool, "evidence": str}],
"notes": str}"""


async def judge_run(
    judge_cfg: JudgeConfig,
    google_api_key: str,
    pass_criteria: list[str],
    turns: list[dict[str, Any]],
    tool_events: list[dict[str, Any]],
) -> dict[str, Any]:
    if not pass_criteria:
        return {"verdict": "skipped", "notes": "Scenario has no PassCriteria."}

    transcript_lines = []
    for t in turns:
        transcript_lines.append(f"Turn {t['turn']}:")
        if t.get("user_text"):
            transcript_lines.append(f"  CALLER: {t['user_text']}")
        if t.get("agent_text"):
            transcript_lines.append(f"  AGENT: {t['agent_text']}")
        if t.get("tool_errors"):
            transcript_lines.append(f"  (tool errors this turn: {t['tool_errors']})")

    tool_lines = [
        json.dumps(
            {
                "kind": e["kind"],
                "turn": e.get("turn"),
                "name": e.get("spec", {}).get("name"),
                "error": e.get("spec", {}).get("error"),
                "duration_ms": e.get("spec", {}).get("duration_ms"),
            },
            ensure_ascii=False,
        )
        for e in tool_events
    ]

    prompt = (
        "PASS CRITERIA:\n"
        + "\n".join(f"- {c}" for c in pass_criteria)
        + "\n\nTRANSCRIPT:\n"
        + ("\n".join(transcript_lines) or "(empty)")
        + "\n\nTOOL SPANS:\n"
        + ("\n".join(tool_lines) or "(none)")
    )

    client = genai.Client(api_key=google_api_key)
    response = await client.aio.models.generate_content(
        model=judge_cfg.model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=JUDGE_SYSTEM,
            temperature=judge_cfg.temperature,
            response_mime_type="application/json",
        ),
    )
    try:
        return json.loads(response.text or "{}")
    except json.JSONDecodeError:
        return {"verdict": "error", "notes": f"Judge returned non-JSON: {(response.text or '')[:500]}"}
