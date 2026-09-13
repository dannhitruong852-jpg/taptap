"""Targeted actor-local repair search for the six C v4 actors that missed QA2.

This module does not alter Golden Set QA2 thresholds. It only defines bounded
actor/intent-local reference and control searches for the fourteen failed intents.
"""
from __future__ import annotations

import copy
from pathlib import Path

REPAIR_ACTORS = ("03", "07", "10", "11", "14", "15")
REPAIR_TARGETS = {
    "03": ("curious_probe",),
    "07": ("curious_probe",),
    "10": ("information_peak", "curious_probe"),
    "11": ("restrained_irony", "curious_probe"),
    "14": ("information_peak", "restrained_irony", "qualification", "curious_probe"),
    "15": ("narrative_build", "information_peak", "qualification", "curious_probe"),
}

# Each entry is an actor-local recalibration centre plus a compact search around it.
# The reference choice comes from the diagnosed failure mode: identity drift and
# pace failures use a same-speaker state that was more stable for that actor.
# Actor 15 has one VCTK recording copied to all states, so its repair is control-only.
REPAIR_SPECS = {
    "03": {
        "curious_probe": ("neutral", (0.48, 0.54, 0.75), 4),
    },
    "07": {
        "curious_probe": ("neutral", (0.52, 0.46, 0.76), 4),
    },
    "10": {
        "information_peak": ("neutral", (0.58, 0.43, 0.76), 4),
        "curious_probe": ("neutral", (0.50, 0.50, 0.76), 4),
    },
    "11": {
        "restrained_irony": ("serious", (0.55, 0.46, 0.78), 4),
        "curious_probe": ("serious", (0.56, 0.44, 0.78), 4),
    },
    "14": {
        "information_peak": ("neutral", (0.56, 0.44, 0.75), 4),
        "restrained_irony": ("neutral", (0.50, 0.48, 0.74), 4),
        "qualification": ("neutral", (0.38, 0.55, 0.73), 4),
        "curious_probe": ("neutral", (0.48, 0.49, 0.75), 4),
    },
    "15": {
        "narrative_build": ("neutral", (0.44, 0.50, 0.72), 4),
        "information_peak": ("lively", (0.48, 0.54, 0.71), 5),
        "qualification": ("serious", (0.34, 0.56, 0.71), 4),
        "curious_probe": ("curious", (0.42, 0.54, 0.72), 4),
    },
}

# Small local perturbations. These stay close enough to the recalibrated centre
# for the existing intent-fidelity proxy while probing Chatterbox stochasticity.
_OFFSETS_4 = (
    ("R1", 0.00, 0.00, 0.00),
    ("R2", -0.04, 0.03, -0.02),
    ("R3", 0.04, -0.02, 0.02),
    ("R4", -0.02, 0.05, -0.04),
)
_OFFSETS_5 = _OFFSETS_4 + (("R5", 0.02, 0.08, -0.05),)


def _bounded(value: float, low: float, high: float) -> float:
    return round(max(low, min(high, value)), 3)


def build_repair_profile(base_profile: dict) -> dict:
    actor_id = str(base_profile["actor_id"])
    if actor_id not in REPAIR_ACTORS:
        raise ValueError(f"actor {actor_id} is not in the six-actor repair set")
    profile = copy.deepcopy(base_profile)
    profile["calibration_id"] = f"{base_profile.get('calibration_id', f'actor-{actor_id}')}-qa2-repair-r1"
    profile["eligible"] = False
    profile["eligible_for"] = []
    profile["selected_candidates"] = {}
    for intent, (reference_state, center, _) in REPAIR_SPECS[actor_id].items():
        local = profile["intent_profiles"][intent]
        local["reference_state"] = reference_state
        local["center"] = {
            "exaggeration": center[0],
            "cfg_weight": center[1],
            "temperature": center[2],
            "repetition_penalty": 1.18,
        }
        local["repair_round"] = 1
        local["repair_reason"] = "actor-local QA2 remediation; Golden Set thresholds unchanged"
    return profile


def build_repair_render_plan(profile: dict, script: dict) -> list[dict]:
    actor_id = str(profile["actor_id"])
    if actor_id not in REPAIR_ACTORS:
        raise ValueError(f"actor {actor_id} is not in the six-actor repair set")
    by_intent = {scene["intent"]: scene for scene in script["scenes"]}
    renders = []
    for intent in REPAIR_TARGETS[actor_id]:
        scene = by_intent[intent]
        reference_state, center, count = REPAIR_SPECS[actor_id][intent]
        offsets = _OFFSETS_5 if count == 5 else _OFFSETS_4
        for variant, dex, dcfg, dtemp in offsets:
            reference = profile["references"][reference_state]
            renders.append({
                "actor_id": actor_id,
                "scene_id": scene["id"],
                "category": scene["category"],
                "intent": intent,
                "intensity": scene["intensity"],
                "text": scene["text"],
                "reference_state": reference_state,
                "reference": reference,
                "variant": variant,
                "delivery": "qa2_repair",
                "exaggeration": _bounded(center[0] + dex, 0.24, 0.88),
                "cfg_weight": _bounded(center[1] + dcfg, 0.25, 0.72),
                "temperature": _bounded(center[2] + dtemp, 0.64, 0.95),
                "repetition_penalty": 1.18,
                "artificial_pause_ms": 0,
                "post_tempo": False,
            })
    return renders


def total_repair_renders() -> int:
    return sum(REPAIR_SPECS[a][intent][2] for a in REPAIR_ACTORS for intent in REPAIR_TARGETS[a])


if __name__ == "__main__":
    print(total_repair_renders())
