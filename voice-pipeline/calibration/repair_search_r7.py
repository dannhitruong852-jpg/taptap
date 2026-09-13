"""Seventh-round final localized QA2 repair for actors 03 and 15."""
from __future__ import annotations

import copy

REPAIR_R7_ACTORS = ("03", "15")
REPAIR_R7_TARGETS = {"03": ("curious_probe",), "15": ("curious_probe",)}


def _repeat(points, n_each):
    out = []
    for point in points:
        out.extend([point] * n_each)
    return tuple(out)


REPAIR_R7_SPECS = {
    "03": {
        "curious_probe": {
            "reference_state": "r4_lowpitch2",
            "synthesis_texts": (
                "If the policy appears efficient on paper, why does its burden still fall so unequally on real people?",
            ),
            "controls": _repeat(
                (
                    (0.40, 0.58, 0.66),
                    (0.39, 0.59, 0.65),
                    (0.41, 0.57, 0.67),
                    (0.38, 0.60, 0.64),
                    (0.42, 0.56, 0.68),
                    (0.40, 0.60, 0.65),
                    (0.39, 0.58, 0.67),
                    (0.41, 0.56, 0.66),
                ),
                2,
            ),
        }
    },
    "15": {
        "curious_probe": {
            "reference_state": "curious",
            "synthesis_texts": (
                "If the policy appears efficient on paper, why does its burden still fall so unequally on real people?",
            ),
            "controls": ((0.28, 0.66, 0.64),) * 16,
        }
    },
}


def build_repair_r7_profile(base_profile: dict) -> dict:
    actor_id = str(base_profile["actor_id"])
    if actor_id not in REPAIR_R7_ACTORS:
        raise ValueError(f"actor {actor_id} is not in repair round seven")
    profile = copy.deepcopy(base_profile)
    profile["calibration_id"] = f"{base_profile.get('calibration_id', f'actor-{actor_id}')}-qa2-repair-r7"
    profile["eligible"] = False
    profile["eligible_for"] = []
    profile["selected_candidates"] = {}
    for intent in REPAIR_R7_TARGETS[actor_id]:
        spec = REPAIR_R7_SPECS[actor_id][intent]
        local = profile["intent_profiles"][intent]
        local["reference_state"] = spec["reference_state"]
        ex, cfg, temp = spec["controls"][0]
        local["center"] = {
            "exaggeration": ex,
            "cfg_weight": cfg,
            "temperature": temp,
            "repetition_penalty": 1.18,
        }
        local["repair_round"] = 7
        local["repair_reason"] = (
            "actor03 identity-first lowpitch2 reference search; actor15 seed-dense naturalness search; QA2 unchanged"
        )
    return profile


def build_repair_r7_render_plan(profile: dict, script: dict) -> list[dict]:
    actor_id = str(profile["actor_id"])
    if actor_id not in REPAIR_R7_ACTORS:
        raise ValueError(f"actor {actor_id} is not in repair round seven")
    by_intent = {scene["intent"]: scene for scene in script["scenes"]}
    renders = []
    counter = 0
    for intent in REPAIR_R7_TARGETS[actor_id]:
        scene = by_intent[intent]
        spec = REPAIR_R7_SPECS[actor_id][intent]
        reference_state = spec["reference_state"]
        reference = profile["references"][reference_state]
        for synthesis_text in spec["synthesis_texts"]:
            for controls in spec["controls"]:
                counter += 1
                renders.append({
                    "actor_id": actor_id,
                    "scene_id": scene["id"],
                    "category": scene["category"],
                    "intent": intent,
                    "intensity": scene["intensity"],
                    "text": scene["text"],
                    "synthesis_text": synthesis_text,
                    "reference_state": reference_state,
                    "reference": reference,
                    "variant": f"Y{counter}",
                    "delivery": "qa2_repair_r7",
                    "exaggeration": controls[0],
                    "cfg_weight": controls[1],
                    "temperature": controls[2],
                    "repetition_penalty": 1.18,
                    "artificial_pause_ms": 0,
                    "post_tempo": False,
                })
    return renders


def total_repair_r7_renders() -> int:
    return sum(
        len(REPAIR_R7_SPECS[a][intent]["synthesis_texts"]) * len(REPAIR_R7_SPECS[a][intent]["controls"])
        for a in REPAIR_R7_ACTORS
        for intent in REPAIR_R7_TARGETS[a]
    )
