"""Build initial actor-local C v4 search profiles for the seven expansion actors.

These are search centres, never production approvals. Real rendered audio must pass
`automated-c-v4-qa-1` before any actor becomes eligible.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "voice-pipeline/config/actor_sources.json"
REGISTRY = ROOT / "voice-pipeline/config/actors.json"

BASE = {
    "03": (0.38, 0.54, 0.74, 0.91),
    "06": (0.46, 0.43, 0.79, 1.00),
    "07": (0.49, 0.42, 0.78, 0.94),
    "10": (0.44, 0.50, 0.77, 0.95),
    "11": (0.52, 0.40, 0.81, 1.02),
    "14": (0.39, 0.53, 0.74, 0.92),
    "15": (0.45, 0.45, 0.78, 0.95),
}

INTENTS = {
    "neutral_explain": ("neutral", 0.000, 0.000, 0.00),
    "serious_analysis": ("serious", -0.035, 0.045, 0.01),
    "warm_explain": ("warm", 0.070, -0.045, 0.00),
    "narrative_build": ("neutral", 0.045, -0.020, 0.01),
    "contrast": ("lively", 0.100, -0.055, 0.00),
    "information_peak": ("lively", 0.125, -0.070, 0.01),
    "restrained_irony": ("ironic", 0.080, 0.005, 0.00),
    "quoted_character": ("emotional", 0.105, -0.040, 0.01),
    "qualification": ("serious", -0.020, 0.030, 0.00),
    "curious_probe": ("curious", 0.075, -0.025, 0.02),
}


def build_profile(actor_id: str) -> dict:
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["actors"]
    registry = {item["id"]: item for item in json.loads(REGISTRY.read_text(encoding="utf-8"))["actors"]}
    src = sources[actor_id]
    actor = registry[actor_id]
    ex, cfg, temp, rate = BASE[actor_id]
    restrained = actor_id in {"03", "14"}
    intents = {}
    for name, (reference, dex, dcfg, dtemp) in INTENTS.items():
        intents[name] = {
            "reference_state": reference,
            "center": {
                "exaggeration": round(ex + dex, 3),
                "cfg_weight": round(cfg + dcfg, 3),
                "temperature": round(temp + dtemp, 3),
                "repetition_penalty": 1.18,
            },
            "step": {
                "exaggeration": 0.065 if restrained else 0.070,
                "cfg_weight": -0.030 if restrained else -0.035,
                "temperature": 0.025,
            },
            "intensity_shift": {
                "exaggeration": 0.020 if restrained else 0.025,
                "cfg_weight": -0.012 if restrained else -0.015,
            },
            "bounds": {
                "exaggeration": [0.24, 0.84 if restrained else 0.88],
                "cfg_weight": [0.25, 0.72],
                "temperature": [0.64, 0.95],
                "repetition_penalty": [1.10, 1.30],
            },
        }
    refs = {state: f"actor{actor_id}-{state}.wav" for state in (
        "neutral", "warm", "lively", "serious", "curious", "ironic", "tense", "emotional"
    )}
    return {
        "schema_version": "c-v4-actor-calibration-1",
        "calibration_id": f"actor-{actor_id}-audition-v1",
        "actor_id": actor_id,
        "source_speaker": src["source_speaker"],
        "source_corpus": src["source_corpus"],
        "source_license": src["source_license"],
        "persona": actor["name"],
        "role": actor["role"],
        "age_impression": src["age_group"],
        "accent": actor["accent"],
        "voice_character": actor["style_note"],
        "references": refs,
        "natural_rate": {"source_baseline": rate, "audition_wpm_range": [125, 180]},
        "intensity_range": [0, 2],
        "long_sentence_stability": "unverified_pending_automated_qa",
        "emotional_plasticity": "unverified_pending_automated_qa",
        "character_consistency": "unverified_pending_automated_qa",
        "known_model_risks": [
            "repetition or truncation on long clauses",
            "identity drift at expressive extremes",
        ],
        "avoid_regions": [
            {"reason": "over-performance risk", "exaggeration_above": 0.88},
            {"reason": "flattened delivery risk", "cfg_weight_above": 0.72},
        ],
        "intent_profiles": intents,
        "selected_candidates": {},
        "human_listening_qa": {
            "status": "not_required_automated_policy",
            "reviewed_by": None,
            "reviewed_at": None,
            "notes": "Production admission is decided by automated-c-v4-qa-1 for this expansion.",
        },
        "eligible": False,
        "eligible_for": [],
    }


def write_profiles(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for actor_id in sorted(BASE):
        (output / f"{actor_id}.json").write_text(
            json.dumps(build_profile(actor_id), indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "voice-pipeline/calibration/actors")
    args = parser.parse_args()
    write_profiles(args.output)
