import unittest

from calibration.repair_search_r8_15 import (
    REPAIR_R8_15_TARGETS,
    REPAIR_R8_15_PROMPT_REFERENCE_STATE,
    REPAIR_R8_15_PROMPT_REFERENCE_FILE,
    REPAIR_R8_15_IDENTITY_REFERENCE_STATE,
    REPAIR_R8_15_CONTROLS,
    build_actor15_r8_profile,
    build_actor15_r8_render_plan,
    total_actor15_r8_renders,
)
from calibration.render_repair_auditions_r8_15 import stable_repair_r8_seed

SCRIPT = {
    "scenes": [{
        "id": "08-probe",
        "intent": "curious_probe",
        "intensity": 1,
        "category": "probe",
        "text": "If the policy appears efficient on paper, why does its burden still fall so unequally on real people?",
    }]
}


def profile():
    return {
        "actor_id": "15",
        "calibration_id": "actor-15-audition-v1",
        "references": {
            "neutral": "actor15-neutral.wav",
            "curious": "actor15-curious.wav",
        },
        "intent_profiles": {
            "curious_probe": {
                "reference_state": "curious",
                "center": {
                    "exaggeration": 0.32,
                    "cfg_weight": 0.62,
                    "temperature": 0.67,
                    "repetition_penalty": 1.18,
                },
            }
        },
        "eligible": False,
        "eligible_for": [],
        "selected_candidates": {},
    }


class Actor15RepairRoundEightTests(unittest.TestCase):
    def test_only_actor15_curious_probe_remains(self):
        self.assertEqual(("curious_probe",), REPAIR_R8_15_TARGETS)
        self.assertEqual(32, total_actor15_r8_renders())

    def test_round_eight_bootstraps_generation_but_keeps_original_identity_reference(self):
        self.assertEqual("r6_x11", REPAIR_R8_15_PROMPT_REFERENCE_STATE)
        self.assertEqual("actor15-08-probe-X11.wav", REPAIR_R8_15_PROMPT_REFERENCE_FILE)
        self.assertEqual("curious", REPAIR_R8_15_IDENTITY_REFERENCE_STATE)

    def test_controls_are_bounded_around_lower_pace_region(self):
        self.assertEqual(32, len(REPAIR_R8_15_CONTROLS))
        unique = set(REPAIR_R8_15_CONTROLS)
        self.assertEqual(4, len(unique))
        expected = {
            (0.24, 0.70, 0.60),
            (0.26, 0.68, 0.62),
            (0.28, 0.66, 0.64),
            (0.30, 0.64, 0.66),
        }
        self.assertEqual(expected, unique)

    def test_profile_keeps_original_identity_reference_and_adds_prompt_reference(self):
        p = build_actor15_r8_profile(profile())
        local = p["intent_profiles"]["curious_probe"]
        self.assertEqual(REPAIR_R8_15_IDENTITY_REFERENCE_STATE, local["reference_state"])
        self.assertEqual(REPAIR_R8_15_PROMPT_REFERENCE_FILE, p["references"][REPAIR_R8_15_PROMPT_REFERENCE_STATE])
        self.assertEqual({
            "exaggeration": 0.24,
            "cfg_weight": 0.70,
            "temperature": 0.60,
            "repetition_penalty": 1.18,
        }, local["center"])

    def test_render_plan_separates_generation_prompt_from_identity_reference(self):
        p = build_actor15_r8_profile(profile())
        renders = build_actor15_r8_render_plan(p, SCRIPT)
        self.assertEqual(32, len(renders))
        for item in renders:
            self.assertEqual(SCRIPT["scenes"][0]["text"], item["text"])
            self.assertEqual(SCRIPT["scenes"][0]["text"], item["synthesis_text"])
            self.assertEqual("curious", item["reference_state"])
            self.assertEqual("actor15-curious.wav", item["reference"])
            self.assertEqual(REPAIR_R8_15_PROMPT_REFERENCE_STATE, item["prompt_reference_state"])
            self.assertEqual(REPAIR_R8_15_PROMPT_REFERENCE_FILE, item["prompt_reference"])
            self.assertEqual(0, item["artificial_pause_ms"])
            self.assertIs(False, item["post_tempo"])
            self.assertEqual(1.18, item["repetition_penalty"])
            self.assertTrue(item["variant"].startswith("Z"))

    def test_seed_is_deterministic_and_variant_specific(self):
        first = stable_repair_r8_seed("15", "08-probe", "Z1")
        self.assertEqual(first, stable_repair_r8_seed("15", "08-probe", "Z1"))
        self.assertNotEqual(first, stable_repair_r8_seed("15", "08-probe", "Z2"))


if __name__ == "__main__":
    unittest.main()
