import unittest

from calibration.repair_search_r9_15 import (
    REPAIR_R9_15_TARGETS,
    REPAIR_R9_15_PROMPT_REFERENCE_STATE,
    REPAIR_R9_15_PROMPT_REFERENCE_FILE,
    REPAIR_R9_15_IDENTITY_REFERENCE_STATE,
    REPAIR_R9_15_CONTROLS,
    build_actor15_r9_profile,
    build_actor15_r9_render_plan,
    total_actor15_r9_renders,
)
from calibration.render_repair_auditions_r9_15 import stable_repair_r9_seed

SCRIPT = {"scenes": [{
    "id": "08-probe",
    "intent": "curious_probe",
    "intensity": 1,
    "category": "probe",
    "text": "If the policy appears efficient on paper, why does its burden still fall so unequally on real people?",
}]}


def profile():
    return {
        "actor_id": "15",
        "calibration_id": "actor-15-audition-v1",
        "references": {"neutral": "actor15-neutral.wav", "curious": "actor15-curious.wav"},
        "intent_profiles": {"curious_probe": {"reference_state": "curious", "center": {
            "exaggeration": 0.32, "cfg_weight": 0.62, "temperature": 0.67, "repetition_penalty": 1.18,
        }}},
        "eligible": False, "eligible_for": [], "selected_candidates": {},
    }


class Actor15RepairRoundNineTests(unittest.TestCase):
    def test_only_actor15_curious_probe_remains(self):
        self.assertEqual(("curious_probe",), REPAIR_R9_15_TARGETS)
        self.assertEqual(32, total_actor15_r9_renders())

    def test_round_nine_keeps_x11_prompt_and_original_identity_reference(self):
        self.assertEqual("r6_x11", REPAIR_R9_15_PROMPT_REFERENCE_STATE)
        self.assertEqual("actor15-08-probe-X11.wav", REPAIR_R9_15_PROMPT_REFERENCE_FILE)
        self.assertEqual("curious", REPAIR_R9_15_IDENTITY_REFERENCE_STATE)

    def test_controls_hold_round_eight_z24_control_point_for_new_seeds(self):
        self.assertEqual(32, len(REPAIR_R9_15_CONTROLS))
        self.assertEqual({(0.28, 0.66, 0.64)}, set(REPAIR_R9_15_CONTROLS))

    def test_profile_preserves_identity_and_immutable_generation_rules(self):
        p = build_actor15_r9_profile(profile())
        local = p["intent_profiles"]["curious_probe"]
        self.assertEqual("curious", local["reference_state"])
        self.assertEqual({
            "exaggeration": 0.28, "cfg_weight": 0.66, "temperature": 0.64, "repetition_penalty": 1.18,
        }, local["center"])

    def test_render_plan_is_bounded_and_no_post_processing(self):
        p = build_actor15_r9_profile(profile())
        renders = build_actor15_r9_render_plan(p, SCRIPT)
        self.assertEqual(32, len(renders))
        for item in renders:
            self.assertEqual("curious", item["reference_state"])
            self.assertEqual("actor15-curious.wav", item["reference"])
            self.assertEqual("r6_x11", item["prompt_reference_state"])
            self.assertEqual("actor15-08-probe-X11.wav", item["prompt_reference"])
            self.assertEqual(0, item["artificial_pause_ms"])
            self.assertIs(False, item["post_tempo"])
            self.assertEqual(1.18, item["repetition_penalty"])
            self.assertTrue(item["variant"].startswith("AA"))

    def test_seed_is_deterministic_and_variant_specific(self):
        first = stable_repair_r9_seed("15", "08-probe", "AA1")
        self.assertEqual(first, stable_repair_r9_seed("15", "08-probe", "AA1"))
        self.assertNotEqual(first, stable_repair_r9_seed("15", "08-probe", "AA2"))


if __name__ == "__main__":
    unittest.main()
