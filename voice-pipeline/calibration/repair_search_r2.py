"""Second targeted actor-local repair search for the C v4 QA2 holdouts.

Round two is evidence-driven from repair round one. It does not change Golden Set
thresholds or post-process audio. It narrows to the six remaining failed cells and
uses actor-local reference states / dense stochastic seeds around the best regions.
"""
from __future__ import annotations

import copy

REPAIR_R2_ACTORS = ("03", "07", "14", "15")
REPAIR_R2_TARGETS = {
    "03": ("curious_probe",),
    "07": ("curious_probe",),
    "14": ("information_peak", "restrained_irony"),
    "15": ("narrative_build", "curious_probe"),
}

# Each spec freezes one actor/intent-local reference and a compact list of
# candidate centres. Repeated centres are intentional: variant-specific seeds
# probe Chatterbox stochasticity without widening controls or weakening QA2.
REPAIR_R2_SPECS = {
    "03": {
        "curious_probe": {
            "reference_state": "ironic",
            "controls": [
                (0.50, 0.53, 0.74), (0.50, 0.53, 0.74),
                (0.52, 0.51, 0.76), (0.52, 0.51, 0.76),
                (0.48, 0.55, 0.72), (0.48, 0.55, 0.72),
                (0.54, 0.50, 0.75), (0.46, 0.57, 0.71),
            ],
        },
    },
    "07": {
        "curious_probe": {
            "reference_state": "lively",
            "controls": [
                (0.57, 0.37, 0.765), (0.57, 0.37, 0.765),
                (0.54, 0.40, 0.75), (0.54, 0.40, 0.75),
                (0.60, 0.35, 0.78), (0.60, 0.35, 0.78),
                (0.52, 0.42, 0.735), (0.56, 0.39, 0.72),
            ],
        },
    },
    "14": {
        "information_peak": {
            "reference_state": "emotional",
            "controls": [
                (0.50, 0.48, 0.75), (0.50, 0.48, 0.75),
                (0.54, 0.45, 0.77), (0.54, 0.45, 0.77),
                (0.46, 0.51, 0.73), (0.46, 0.51, 0.73),
                (0.58, 0.43, 0.79), (0.48, 0.53, 0.71),
            ],
        },
        "restrained_irony": {
            "reference_state": "emotional",
            "controls": [
                (0.46, 0.52, 0.73), (0.46, 0.52, 0.73),
                (0.50, 0.49, 0.75), (0.50, 0.49, 0.75),
                (0.42, 0.55, 0.71), (0.42, 0.55, 0.71),
                (0.54, 0.47, 0.77), (0.44, 0.57, 0.69),
            ],
        },
    },
    "15": {
        "narrative_build": {
            "reference_state": "neutral",
            "controls": [
                (0.40, 0.53, 0.70), (0.40, 0.53, 0.70),
                (0.40, 0.53, 0.70), (0.40, 0.53, 0.70),
                (0.44, 0.50, 0.72), (0.44, 0.50, 0.72),
                (0.38, 0.56, 0.68), (0.38, 0.56, 0.68),
                (0.42, 0.55, 0.69), (0.46, 0.48, 0.71),
            ],
        },
        "curious_probe": {
            "reference_state": "curious",
            "controls": [
                (0.38, 0.57, 0.70), (0.38, 0.57, 0.70),
                (0.38, 0.57, 0.70), (0.38, 0.57, 0.70),
                (0.36, 0.60, 0.68), (0.36, 0.60, 0.68),
                (0.40, 0.58, 0.69), (0.40, 0.58, 0.69),
            ],
        },
    },
}


def build_repair_r2_profile(base_profile: dict) -> dict:
    actor_id = str(base_profile["actor_id"])
    if actor_id not in REPAIR_R2_ACTORS:
        raise ValueError(f"actor {actor_id} is not in repair round two")
    profile = copy.deepcopy(base_profile)
    profile["calibration_id"] = f"{base_profile.get('calibration_id', f'actor-{actor_id}')}-qa2-repair-r2"
    profile["eligible"] = False
    profile["eligible_for"] = []
    profile["selected_candidates"] = {}
    for intent in REPAIR_R2_TARGETS[actor_id]:
        spec = REPAIR_R2_SPECS[actor_id][intent]
        first = spec["controls"][0]
        local = profile["intent_profiles"][intent]
        local["reference_state"] = spec["reference_state"]
        local["center"] = {
            "exaggeration": first[0],
            "cfg_weight": first[1],
            "temperature": first[2],
            "repetition_penalty": 1.18,
        }
        local["repair_round"] = 2
        local["repair_reason"] = "evidence-driven actor-local QA2 remediation; thresholds unchanged"
    return profile


def build_repair_r2_render_plan(profile: dict, script: dict) -> list[dict]:
    actor_id = str(profile["actor_id"])
    if actor_id not in REPAIR_R2_ACTORS:
        raise ValueError(f"actor {actor_id} is not in repair round two")
    by_intent = {scene["intent"]: scene for scene in script["scenes"]}
    renders = []
    for intent in REPAIR_R2_TARGETS[actor_id]:
        scene = by_intent[intent]
        spec = REPAIR_R2_SPECS[actor_id][intent]
        reference_state = spec["reference_state"]
        reference = profile["references"][reference_state]
        for index, controls in enumerate(spec["controls"], start=1):
            renders.append({
                "actor_id": actor_id,
                "scene_id": scene["id"],
                "category": scene["category"],
                "intent": intent,
                "intensity": scene["intensity"],
                "text": scene["text"],
                "reference_state": reference_state,
                "reference": reference,
                "variant": f"S{index}",
                "delivery": "qa2_repair_r2",
                "exaggeration": controls[0],
                "cfg_weight": controls[1],
                "temperature": controls[2],
                "repetition_penalty": 1.18,
                "artificial_pause_ms": 0,
                "post_tempo": False,
            })
    return renders


def total_repair_r2_renders() -> int:
    return sum(
        len(REPAIR_R2_SPECS[actor][intent]["controls"])
        for actor in REPAIR_R2_ACTORS
        for intent in REPAIR_R2_TARGETS[actor]
    )
