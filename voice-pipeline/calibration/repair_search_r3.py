"""Third evidence-driven actor-local repair search for C v4 QA2 holdouts.

Round three keeps the Golden Set QA2 policy immutable. It targets only the four
actor/intent cells still failing after round two and uses same-actor evidence to
choose reference states and dense stochastic seeds around the most promising
control regions. No artificial pauses or post-tempo processing are allowed.
"""
from __future__ import annotations

import copy

REPAIR_R3_ACTORS = ("03", "14", "15")
REPAIR_R3_TARGETS = {
    "03": ("curious_probe",),
    "14": ("information_peak",),
    "15": ("narrative_build", "curious_probe"),
}


def _repeat_controls(points, counts):
    out = []
    for point, count in zip(points, counts):
        out.extend([point] * count)
    return out


# Evidence basis:
# - actor03: warm reference produced the strongest same-actor identity sample
#   (0.9962), while round-two ironic reference regressed identity stability.
# - actor14: neutral reference contains same-actor 151.8/161.4 WPM examples,
#   proving this voice can naturally cross the 152.5 WPM information_peak floor.
# - actor15 narrative: round two is already clean on every dimension except exact
#   transcript WER, so use many seeds around the clearest low-temp/high-cfg region.
# - actor15 curious_probe: round-one R2 is closest; push slightly lower temperature
#   and higher CFG while staying in actor-local controls, seeking slower output.
REPAIR_R3_SPECS = {
    "03": {
        "curious_probe": {
            "reference_state": "warm",
            "controls": _repeat_controls(
                [
                    (0.45, 0.495, 0.74),
                    (0.43, 0.515, 0.72),
                    (0.47, 0.485, 0.75),
                    (0.41, 0.535, 0.70),
                ],
                [4, 4, 4, 4],
            ),
        },
    },
    "14": {
        "information_peak": {
            "reference_state": "neutral",
            "controls": _repeat_controls(
                [
                    (0.455, 0.500, 0.765),
                    (0.430, 0.515, 0.755),
                    (0.405, 0.530, 0.745),
                    (0.390, 0.540, 0.735),
                ],
                [4, 4, 4, 4],
            ),
        },
    },
    "15": {
        "narrative_build": {
            "reference_state": "neutral",
            "controls": _repeat_controls(
                [
                    (0.38, 0.56, 0.68),
                    (0.40, 0.55, 0.69),
                    (0.36, 0.58, 0.67),
                    (0.42, 0.54, 0.70),
                ],
                [6, 6, 6, 6],
            ),
        },
        "curious_probe": {
            "reference_state": "curious",
            "controls": _repeat_controls(
                [
                    (0.38, 0.60, 0.68),
                    (0.36, 0.62, 0.67),
                    (0.40, 0.59, 0.69),
                    (0.34, 0.64, 0.66),
                ],
                [4, 4, 4, 4],
            ),
        },
    },
}


def build_repair_r3_profile(base_profile: dict) -> dict:
    actor_id = str(base_profile["actor_id"])
    if actor_id not in REPAIR_R3_ACTORS:
        raise ValueError(f"actor {actor_id} is not in repair round three")
    profile = copy.deepcopy(base_profile)
    profile["calibration_id"] = f"{base_profile.get('calibration_id', f'actor-{actor_id}')}-qa2-repair-r3"
    profile["eligible"] = False
    profile["eligible_for"] = []
    profile["selected_candidates"] = {}
    for intent in REPAIR_R3_TARGETS[actor_id]:
        spec = REPAIR_R3_SPECS[actor_id][intent]
        first = spec["controls"][0]
        local = profile["intent_profiles"][intent]
        local["reference_state"] = spec["reference_state"]
        local["center"] = {
            "exaggeration": first[0],
            "cfg_weight": first[1],
            "temperature": first[2],
            "repetition_penalty": 1.18,
        }
        local["repair_round"] = 3
        local["repair_reason"] = "evidence-driven actor-local QA2 remediation; thresholds unchanged"
    return profile


def build_repair_r3_render_plan(profile: dict, script: dict) -> list[dict]:
    actor_id = str(profile["actor_id"])
    if actor_id not in REPAIR_R3_ACTORS:
        raise ValueError(f"actor {actor_id} is not in repair round three")
    by_intent = {scene["intent"]: scene for scene in script["scenes"]}
    renders = []
    for intent in REPAIR_R3_TARGETS[actor_id]:
        scene = by_intent[intent]
        spec = REPAIR_R3_SPECS[actor_id][intent]
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
                "variant": f"T{index}",
                "delivery": "qa2_repair_r3",
                "exaggeration": controls[0],
                "cfg_weight": controls[1],
                "temperature": controls[2],
                "repetition_penalty": 1.18,
                "artificial_pause_ms": 0,
                "post_tempo": False,
            })
    return renders


def total_repair_r3_renders() -> int:
    return sum(
        len(REPAIR_R3_SPECS[actor][intent]["controls"])
        for actor in REPAIR_R3_ACTORS
        for intent in REPAIR_R3_TARGETS[actor]
    )
