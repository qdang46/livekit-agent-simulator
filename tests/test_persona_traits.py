from livekit_agent_simulator.persona_traits import expand_traits, list_trait_ids
from livekit_agent_simulator.scenario import Scenario


def test_trait_library_has_core_tags():
    ids = list_trait_ids()
    assert "impatient" in ids
    assert "interrupts" in ids
    assert "quiet" in ids


def test_expand_traits_known_and_unknown():
    lines = expand_traits(["impatient", "custom_tag_xyz"])
    blob = " ".join(lines).lower()
    assert "time" in blob or "quick" in blob or "short" in blob
    assert "custom_tag_xyz" in blob


def test_persona_prompt_includes_trait_library():
    s = Scenario(
        id="t",
        path=__import__("pathlib").Path("t.jsonl"),
        locale="en-US",
        persona={
            "brief": "Need support.",
            "traits": ["impatient", "interrupts"],
            "language": "vi-VN",
        },
    )
    prompt = s.persona_system_prompt()
    assert "vi-VN" in prompt
    assert "impatient" in prompt or "time" in prompt.lower()
