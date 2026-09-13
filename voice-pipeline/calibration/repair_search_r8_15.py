"""Actor15-only Round 8: bootstrap generation from the best Round 6 probe while preserving the original identity gate."""
from __future__ import annotations

import copy

REPAIR_R8_15_TARGETS = ("curious_probe",)
REPAIR_R8_15_PROMPT_REFERENCE_STATE = "r6_x11"
REPAIR_R8_15_PROMPT_REFERENCE_FILE = "actor15-08-probe-X11.wav"
REPAIR_R8_15_IDENTITY_REFERENCE_STATE = "curious"

_BASE_CONTROLS = (
    (0.24, 0.70, 0.60),
    (0.26, 0.68, 0.62),
    (0.28, 0.66, 0.64),
    (0.30, 0.64, 0.66),
)
REPAIR_R8_15_CONTROLS = tuple(control for control in _BASE_CONTROLS for _ in range(8))


def build_actor15_r8_profile(base_profile: dict) -> dict:
    if str(base_profile["actor_id"]) != "15":
        raise ValueError("actor15 round eight only accepts actor 15")
    profile = copy.deepcopy(base_profile)
    profile["calibration_id"] = f"{base_profile.get('calibration_id', 'actor-15')}-qa2-repair-r8"
    profile["eligible"] = False
    profile["eligible_for"] = []
    profile["selected_candidates"] = {}
    profile["references"][REPAIR_R8_15_PROMPT_REFERENCE_STATE] = REPAIR_R8_15_PROMPT_REFERENCE_FILE
    local = profile["intent_profiles"]["curious_probe"]
    local["reference_state"] = REPAIR_R8_15_IDENTITY_REFERENCE_STATE
    ex, cfg, temp = REPAIR_R8_15_CONTROLS[0]
    local["center"] = {
        "exaggeration": ex,
        "cfg_weight": cfg,
        "temperature": temp,
        "repetition_penalty": 1.18,
    }
    local["repair_round"] = 8
    local["repair_reason"] = (
        "generation-prompt bootstrap from actor15 Round 6 X11; identity scoring remains against original licensed p225 curious reference; QA2 unchanged"
    )
    return profile


def build_actor15_r8_render_plan(profile: dict, script: dict) -> list[dict]:
    if str(profile["actor_id"]) != "15":
        raise ValueError("actor15 round eight only accepts actor 15")
    scene = next(s for s in script["scenes"] if s["intent"] == "curious_probe")
    identity_reference = profile["references"][REPAIR_R8_15_IDENTITY_REFERENCE_STATE]
    prompt_reference = profile["references"][REPAIR_R8_15_PROMPT_REFERENCE_STATE]
    renders = []
    for index, controls in enumerate(REPAIR_R8_15_CONTROLS, start=1):
        renders.append({
            "actor_id": "15",
            "scene_id": scene["id"],
            "category": scene["category"],
            "intent": "curious_probe",
            "intensity": scene["intensity"],
            "text": scene["text"],
            "synthesis_text": scene["text"],
            "reference_state": REPAIR_R8_15_IDENTITY_REFERENCE_STATE,
            "reference": identity_reference,
            "prompt_reference_state": REPAIR_R8_15_PROMPT_REFERENCE_STATE,
            "prompt_reference": prompt_reference,
            "variant": f"Z{index}",
            "delivery": "qa2_repair_r8_actor15_bootstrap",
            "exaggeration": controls[0],
            "cfg_weight": controls[1],
            "temperature": controls[2],
            "repetition_penalty": 1.18,
            "artificial_pause_ms": 0,
            "post_tempo": False,
        })
    return renders


def total_actor15_r8_renders() -> int:
    return len(REPAIR_R8_15_CONTROLS)
