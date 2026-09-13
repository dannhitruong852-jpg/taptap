"""Parallel fourth-round repair for actors 03 and 14 only.

After three bounded control-search rounds, actor03 remains identity-limited on
curious_probe and actor14 remains pace-limited on information_peak. Round four
therefore changes same-speaker reference strategy instead of weakening QA2.
"""
from __future__ import annotations

import copy

REPAIR_R4_ACTORS = ("03", "14")
REPAIR_R4_TARGETS = {
    "03": ("curious_probe",),
    "14": ("information_peak",),
}

REPAIR_R4_SPECS = {
    "03": {
        "curious_probe": {
            "reference_states": ("warm", "serious", "r4_lowpitch1", "r4_lowpitch2"),
            "controls": (
                (0.46, 0.51, 0.74),
                (0.48, 0.50, 0.75),
                (0.44, 0.52, 0.72),
                (0.50, 0.49, 0.76),
                (0.42, 0.54, 0.70),
                (0.52, 0.49, 0.73),
            ),
        },
    },
    "14": {
        "information_peak": {
            "reference_states": ("r4_fast1", "r4_fast2"),
            "controls": (
                (0.44, 0.48, 0.78),
                (0.46, 0.46, 0.80),
                (0.42, 0.50, 0.79),
                (0.48, 0.44, 0.82),
                (0.40, 0.52, 0.77),
                (0.45, 0.50, 0.81),
                (0.43, 0.47, 0.83),
                (0.47, 0.45, 0.76),
            ),
        },
    },
}

EXTRA_REFERENCE_FILENAMES = {
    "03": {
        "r4_lowpitch1": "actor03-r4_lowpitch1.wav",
        "r4_lowpitch2": "actor03-r4_lowpitch2.wav",
    },
    "14": {
        "r4_fast1": "actor14-r4_fast1.wav",
        "r4_fast2": "actor14-r4_fast2.wav",
    },
}


def build_repair_r4_profile(base_profile: dict) -> dict:
    actor_id = str(base_profile["actor_id"])
    if actor_id not in REPAIR_R4_ACTORS:
        raise ValueError(f"actor {actor_id} is not in repair round four")
    profile = copy.deepcopy(base_profile)
    profile["calibration_id"] = f"{base_profile.get('calibration_id', f'actor-{actor_id}')}-qa2-repair-r4"
    profile["eligible"] = False
    profile["eligible_for"] = []
    profile["selected_candidates"] = {}
    profile["references"].update(EXTRA_REFERENCE_FILENAMES[actor_id])
    for intent in REPAIR_R4_TARGETS[actor_id]:
        spec = REPAIR_R4_SPECS[actor_id][intent]
        local = profile["intent_profiles"][intent]
        local["reference_state"] = spec["reference_states"][0]
        first = spec["controls"][0]
        local["center"] = {
            "exaggeration": first[0],
            "cfg_weight": first[1],
            "temperature": first[2],
            "repetition_penalty": 1.18,
        }
        local["repair_round"] = 4
        local["repair_reason"] = "same-speaker reference-strategy remediation; Golden Set QA2 unchanged"
    return profile


def build_repair_r4_render_plan(profile: dict, script: dict) -> list[dict]:
    actor_id = str(profile["actor_id"])
    if actor_id not in REPAIR_R4_ACTORS:
        raise ValueError(f"actor {actor_id} is not in repair round four")
    by_intent = {scene["intent"]: scene for scene in script["scenes"]}
    renders = []
    counter = 0
    for intent in REPAIR_R4_TARGETS[actor_id]:
        scene = by_intent[intent]
        spec = REPAIR_R4_SPECS[actor_id][intent]
        for reference_state in spec["reference_states"]:
            reference = profile["references"][reference_state]
            for controls in spec["controls"]:
                counter += 1
                renders.append({
                    "actor_id": actor_id,
                    "scene_id": scene["id"],
                    "category": scene["category"],
                    "intent": intent,
                    "intensity": scene["intensity"],
                    "text": scene["text"],
                    "reference_state": reference_state,
                    "reference": reference,
                    "variant": f"U{counter}",
                    "delivery": "qa2_repair_r4",
                    "exaggeration": controls[0],
                    "cfg_weight": controls[1],
                    "temperature": controls[2],
                    "repetition_penalty": 1.18,
                    "artificial_pause_ms": 0,
                    "post_tempo": False,
                })
    return renders


def total_repair_r4_renders() -> int:
    return sum(
        len(REPAIR_R4_SPECS[a][intent]["reference_states"]) * len(REPAIR_R4_SPECS[a][intent]["controls"])
        for a in REPAIR_R4_ACTORS for intent in REPAIR_R4_TARGETS[a]
    )
