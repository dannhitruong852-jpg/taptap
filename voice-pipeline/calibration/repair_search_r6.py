"""Sixth-round bounded repair for the final two QA2 holdouts: actors 03 and 15."""
from __future__ import annotations

import copy

REPAIR_R6_ACTORS = ("03", "15")
REPAIR_R6_TARGETS = {
    "03": ("curious_probe",),
    "15": ("curious_probe",),
}


def _repeat(point, n):
    return tuple(point for _ in range(n))


REPAIR_R6_SPECS = {
    "03": {
        "curious_probe": {
            # U5 was the only historical candidate with all gates passing except
            # internal silence, so round six freezes its proven control/reference
            # point and searches seeds only. No punctuation change is introduced.
            "reference_state": "warm",
            "synthesis_texts": (
                "If the policy appears efficient on paper, why does its burden still fall so unequally on real people?",
            ),
            "controls": _repeat((0.42, 0.54, 0.70), 16),
        }
    },
    "15": {
        "curious_probe": {
            # V30/V31 and W3 show identity/transcript/fidelity are stable; the only
            # persistent blocker is naturalness. Push a small, bounded slower region
            # by lowering exaggeration/temperature and raising CFG while keeping the
            # canonical comma text and same-speaker curious reference.
            "reference_state": "curious",
            "synthesis_texts": (
                "If the policy appears efficient on paper, why does its burden still fall so unequally on real people?",
            ),
            "controls": (
                (0.30, 0.64, 0.66),
                (0.29, 0.65, 0.65),
                (0.28, 0.66, 0.64),
                (0.31, 0.64, 0.65),
                (0.30, 0.64, 0.66),
                (0.29, 0.65, 0.65),
                (0.28, 0.66, 0.64),
                (0.31, 0.64, 0.65),
                (0.30, 0.64, 0.66),
                (0.29, 0.65, 0.65),
                (0.28, 0.66, 0.64),
                (0.31, 0.64, 0.65),
                (0.30, 0.64, 0.66),
                (0.29, 0.65, 0.65),
                (0.28, 0.66, 0.64),
                (0.31, 0.64, 0.65),
            ),
        }
    },
}


def build_repair_r6_profile(base_profile: dict) -> dict:
    actor_id = str(base_profile["actor_id"])
    if actor_id not in REPAIR_R6_ACTORS:
        raise ValueError(f"actor {actor_id} is not in repair round six")
    profile = copy.deepcopy(base_profile)
    profile["calibration_id"] = f"{base_profile.get('calibration_id', f'actor-{actor_id}')}-qa2-repair-r6"
    profile["eligible"] = False
    profile["eligible_for"] = []
    profile["selected_candidates"] = {}
    for intent in REPAIR_R6_TARGETS[actor_id]:
        spec = REPAIR_R6_SPECS[actor_id][intent]
        local = profile["intent_profiles"][intent]
        local["reference_state"] = spec["reference_state"]
        ex, cfg, temp = spec["controls"][0]
        local["center"] = {
            "exaggeration": ex,
            "cfg_weight": cfg,
            "temperature": temp,
            "repetition_penalty": 1.18,
        }
        local["repair_round"] = 6
        local["repair_reason"] = "single-blocker localized QA2 remediation; thresholds unchanged"
    return profile


def build_repair_r6_render_plan(profile: dict, script: dict) -> list[dict]:
    actor_id = str(profile["actor_id"])
    if actor_id not in REPAIR_R6_ACTORS:
        raise ValueError(f"actor {actor_id} is not in repair round six")
    by_intent = {scene["intent"]: scene for scene in script["scenes"]}
    renders = []
    counter = 0
    for intent in REPAIR_R6_TARGETS[actor_id]:
        scene = by_intent[intent]
        spec = REPAIR_R6_SPECS[actor_id][intent]
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
                    "alias_id": f"r6a{alias_index}",
                    "reference_state": reference_state,
                    "reference": reference,
                    "variant": f"X{counter}",
                    "delivery": "qa2_repair_r6",
                    "exaggeration": controls[0],
                    "cfg_weight": controls[1],
                    "temperature": controls[2],
                    "repetition_penalty": 1.18,
                    "artificial_pause_ms": 0,
                    "post_tempo": False,
                })
    return renders


def total_repair_r6_renders() -> int:
    return sum(
        len(REPAIR_R6_SPECS[a][intent]["synthesis_texts"]) * len(REPAIR_R6_SPECS[a][intent]["controls"])
        for a in REPAIR_R6_ACTORS
        for intent in REPAIR_R6_TARGETS[a]
    )
