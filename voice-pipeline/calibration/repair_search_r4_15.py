"""Fourth-round actor15 repair: pronunciation/prosody input remediation with QA2 unchanged."""
from __future__ import annotations

import copy

REPAIR_R4_15_TARGETS = ("narrative_build", "curious_probe")

REPAIR_R4_15_SPECS = {
    "narrative_build": {
        "reference_state": "neutral",
        "synthesis_texts": (
            "Late one autumn evening, a young researcher found an unopened letter waiting beneath the lab-oratory door.",
            "Late one autumn evening, a young researcher found an unopened letter waiting beneath the la-boratory door.",
            "Late one autumn evening, a young researcher found an unopened letter waiting beneath the labo-ratory door.",
            "Late one autumn evening, a young researcher found an unopened letter waiting beneath the laboratory door.",
        ),
        "controls": (
            (0.38, 0.58, 0.67),
            (0.40, 0.56, 0.68),
            (0.36, 0.60, 0.66),
            (0.42, 0.55, 0.69),
        ),
    },
    "curious_probe": {
        "reference_state": "curious",
        "synthesis_texts": (
            "If the policy appears efficient on paper, why does its burden still fall so unequally on real people?",
            "If the policy appears efficient on paper... why does its burden still fall so unequally on real people?",
            "If the policy appears efficient on paper — why does its burden still fall so unequally on real people?",
            "If the policy appears efficient on paper; why does its burden still fall so unequally on real people?",
        ),
        "controls": (
            (0.34, 0.60, 0.68),
            (0.36, 0.58, 0.69),
            (0.32, 0.62, 0.67),
            (0.38, 0.59, 0.68),
        ),
    },
}


def build_actor15_r4_profile(base_profile: dict) -> dict:
    if str(base_profile["actor_id"]) != "15":
        raise ValueError("actor15 round four only accepts actor 15")
    profile = copy.deepcopy(base_profile)
    profile["calibration_id"] = f"{base_profile.get('calibration_id', 'actor-15')}-qa2-repair-r4"
    profile["eligible"] = False
    profile["eligible_for"] = []
    profile["selected_candidates"] = {}
    for intent in REPAIR_R4_15_TARGETS:
        spec = REPAIR_R4_15_SPECS[intent]
        first = spec["controls"][0]
        local = profile["intent_profiles"][intent]
        local["reference_state"] = spec["reference_state"]
        local["center"] = {
            "exaggeration": first[0],
            "cfg_weight": first[1],
            "temperature": first[2],
            "repetition_penalty": 1.18,
        }
        local["repair_round"] = 4
        local["repair_reason"] = "pronunciation/prosody input remediation; canonical QA transcript and Golden Set QA2 unchanged"
    return profile


def build_actor15_r4_render_plan(profile: dict, script: dict) -> list[dict]:
    if str(profile["actor_id"]) != "15":
        raise ValueError("actor15 round four only accepts actor 15")
    by_intent = {scene["intent"]: scene for scene in script["scenes"]}
    renders = []
    counter = 0
    for intent in REPAIR_R4_15_TARGETS:
        scene = by_intent[intent]
        spec = REPAIR_R4_15_SPECS[intent]
        reference_state = spec["reference_state"]
        reference = profile["references"][reference_state]
        for alias_index, synthesis_text in enumerate(spec["synthesis_texts"], start=1):
            for controls in spec["controls"]:
                counter += 1
                renders.append({
                    "actor_id": "15",
                    "scene_id": scene["id"],
                    "category": scene["category"],
                    "intent": intent,
                    "intensity": scene["intensity"],
                    "text": scene["text"],
                    "synthesis_text": synthesis_text,
                    "alias_id": f"a{alias_index}",
                    "reference_state": reference_state,
                    "reference": reference,
                    "variant": f"V{counter}",
                    "delivery": "qa2_repair_r4_actor15",
                    "exaggeration": controls[0],
                    "cfg_weight": controls[1],
                    "temperature": controls[2],
                    "repetition_penalty": 1.18,
                    "artificial_pause_ms": 0,
                    "post_tempo": False,
                })
    return renders


def total_actor15_r4_renders() -> int:
    return sum(
        len(REPAIR_R4_15_SPECS[intent]["synthesis_texts"]) * len(REPAIR_R4_15_SPECS[intent]["controls"])
        for intent in REPAIR_R4_15_TARGETS
    )
