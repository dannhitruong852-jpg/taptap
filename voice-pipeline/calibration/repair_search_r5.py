"""Fifth-round bounded repair for the final two QA2 holdouts: actors 03 and 15."""
from __future__ import annotations

import copy

REPAIR_R5_ACTORS = ("03", "15")
REPAIR_R5_TARGETS = {
    "03": ("curious_probe",),
    "15": ("curious_probe",),
}


def _repeat(points, counts):
    out = []
    for p, n in zip(points, counts):
        out.extend([p] * n)
    return tuple(out)


REPAIR_R5_SPECS = {
    "03": {
        "curious_probe": {
            "reference_state": "warm",
            "synthesis_texts": (
                "If the policy appears efficient on paper, why does its burden still fall so unequally on real people?",
                "If the policy appears efficient on paper why does its burden still fall so unequally on real people?",
            ),
            "controls": (
                (0.42, 0.54, 0.70),
                (0.41, 0.54, 0.70),
                (0.43, 0.53, 0.70),
                (0.42, 0.55, 0.69),
                (0.40, 0.55, 0.71),
                (0.44, 0.52, 0.71),
                (0.41, 0.53, 0.72),
                (0.43, 0.54, 0.69),
            ),
        }
    },
    "15": {
        "curious_probe": {
            "reference_state": "curious",
            "synthesis_texts": (
                "If the policy appears efficient on paper; why does its burden still fall so unequally on real people?",
            ),
            "controls": _repeat(
                (
                    (0.32, 0.62, 0.67),
                    (0.31, 0.63, 0.67),
                    (0.33, 0.61, 0.67),
                    (0.30, 0.64, 0.66),
                    (0.34, 0.60, 0.68),
                    (0.35, 0.59, 0.68),
                    (0.36, 0.58, 0.69),
                    (0.33, 0.62, 0.68),
                ),
                (2, 2, 2, 2, 2, 2, 2, 2),
            ),
        }
    },
}


def build_repair_r5_profile(base_profile: dict) -> dict:
    actor_id = str(base_profile["actor_id"])
    if actor_id not in REPAIR_R5_ACTORS:
        raise ValueError(f"actor {actor_id} is not in repair round five")
    profile = copy.deepcopy(base_profile)
    profile["calibration_id"] = f"{base_profile.get('calibration_id', f'actor-{actor_id}')}-qa2-repair-r5"
    profile["eligible"] = False
    profile["eligible_for"] = []
    profile["selected_candidates"] = {}
    for intent in REPAIR_R5_TARGETS[actor_id]:
        spec = REPAIR_R5_SPECS[actor_id][intent]
        local = profile["intent_profiles"][intent]
        local["reference_state"] = spec["reference_state"]
        ex, cfg, temp = spec["controls"][0]
        local["center"] = {
            "exaggeration": ex,
            "cfg_weight": cfg,
            "temperature": temp,
            "repetition_penalty": 1.18,
        }
        local["repair_round"] = 5
        local["repair_reason"] = "final localized QA2 remediation; thresholds unchanged"
    return profile


def build_repair_r5_render_plan(profile: dict, script: dict) -> list[dict]:
    actor_id = str(profile["actor_id"])
    if actor_id not in REPAIR_R5_ACTORS:
        raise ValueError(f"actor {actor_id} is not in repair round five")
    by_intent = {scene["intent"]: scene for scene in script["scenes"]}
    renders = []
    counter = 0
    for intent in REPAIR_R5_TARGETS[actor_id]:
        scene = by_intent[intent]
        spec = REPAIR_R5_SPECS[actor_id][intent]
        reference_state = spec["reference_state"]
        reference = profile["references"][reference_state]
        for alias_index, synthesis_text in enumerate(spec["synthesis_texts"], start=1):
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
                    "alias_id": f"r5a{alias_index}",
                    "reference_state": reference_state,
                    "reference": reference,
                    "variant": f"W{counter}",
                    "delivery": "qa2_repair_r5",
                    "exaggeration": controls[0],
                    "cfg_weight": controls[1],
                    "temperature": controls[2],
                    "repetition_penalty": 1.18,
                    "artificial_pause_ms": 0,
                    "post_tempo": False,
                })
    return renders


def total_repair_r5_renders() -> int:
    return sum(
        len(REPAIR_R5_SPECS[a][intent]["synthesis_texts"]) * len(REPAIR_R5_SPECS[a][intent]["controls"])
        for a in REPAIR_R5_ACTORS
        for intent in REPAIR_R5_TARGETS[a]
    )
