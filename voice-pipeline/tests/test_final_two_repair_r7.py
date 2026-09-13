import unittest

from calibration.repair_search_r7 import (
    REPAIR_R7_ACTORS,
    REPAIR_R7_TARGETS,
    REPAIR_R7_SPECS,
    build_repair_r7_profile,
    build_repair_r7_render_plan,
    total_repair_r7_renders,
)
from calibration.render_repair_auditions_r7 import stable_repair_r7_seed

SCRIPT = {
    "scenes": [{
        "id": "08-probe",
        "intent": "curious_probe",
        "intensity": 1,
        "category": "probe",
        "text": "If the policy appears efficient on paper, why does its burden still fall so unequally on real people?",
    }]
}


def profile(actor_id):
    refs = {state: f"actor{actor_id}-{state}.wav" for state in (
        "neutral", "warm", "lively", "serious", "curious", "ironic", "tense", "emotional"
    )}
    if actor_id == "03":
        refs["r4_lowpitch2"] = "actor03-r4_lowpitch2.wav"
    return {
        "actor_id": actor_id,
        "calibration_id": f"actor-{actor_id}-audition-v1",
        "references": refs,
        "intent_profiles": {
            "curious_probe": {
                "reference_state": "neutral",
                "center": {
                    "exaggeration": 0.5,
                    "cfg_weight": 0.5,
                    "temperature": 0.75,
                    "repetition_penalty": 1.18,
                },
            }
        },
        "eligible": False,
        "eligible_for": [],
        "selected_candidates": {},
    }


class FinalTwoRepairRoundSevenTests(unittest.TestCase):
    def test_only_final_two_curious_probe_cells_are_rendered(self):
        self.assertEqual(REPAIR_R7_ACTORS, ("03", "15"))
        self.assertEqual(REPAIR_R7_TARGETS, {"03": ("curious_probe",), "15": ("curious_probe",)})
        self.assertEqual(32, total_repair_r7_renders())

    def test_actor03_switches_to_identity_stable_lowpitch2_reference(self):
        spec = REPAIR_R7_SPECS["03"]["curious_probe"]
        self.assertEqual("r4_lowpitch2", spec["reference_state"])
        self.assertEqual(16, len(spec["controls"]))
        self.assertTrue(all(0.38 <= ex <= 0.42 for ex, _, _ in spec["controls"]))
        self.assertTrue(all(0.56 <= cfg <= 0.60 for _, cfg, _ in spec["controls"]))
        self.assertTrue(all(0.64 <= temp <= 0.68 for _, _, temp in spec["controls"]))

    def test_actor15_is_seed_dense_at_best_round_six_control(self):
        spec = REPAIR_R7_SPECS["15"]["curious_probe"]
        self.assertEqual("curious", spec["reference_state"])
        self.assertEqual(16, len(spec["controls"]))
        self.assertEqual({(0.28, 0.66, 0.64)}, set(spec["controls"]))

    def test_profile_center_matches_round_seven_reference_and_primary_control(self):
        for actor_id in REPAIR_R7_ACTORS:
            repaired = build_repair_r7_profile(profile(actor_id))
            spec = REPAIR_R7_SPECS[actor_id]["curious_probe"]
            local = repaired["intent_profiles"]["curious_probe"]
            self.assertEqual(spec["reference_state"], local["reference_state"])
            ex, cfg, temp = spec["controls"][0]
            self.assertEqual(ex, local["center"]["exaggeration"])
            self.assertEqual(cfg, local["center"]["cfg_weight"])
            self.assertEqual(temp, local["center"]["temperature"])

    def test_round_seven_keeps_immutable_quality_rules(self):
        for actor_id in REPAIR_R7_ACTORS:
            repaired = build_repair_r7_profile(profile(actor_id))
            renders = build_repair_r7_render_plan(repaired, SCRIPT)
            self.assertEqual(16, len(renders))
            for item in renders:
                self.assertEqual(0, item["artificial_pause_ms"])
                self.assertIs(False, item["post_tempo"])
                self.assertEqual(1.18, item["repetition_penalty"])
                self.assertEqual("curious_probe", item["intent"])
                self.assertTrue(item["variant"].startswith("Y"))

    def test_round_seven_seed_is_deterministic_and_actor_specific(self):
        first = stable_repair_r7_seed("03", "08-probe", "Y1")
        self.assertEqual(first, stable_repair_r7_seed("03", "08-probe", "Y1"))
        self.assertNotEqual(first, stable_repair_r7_seed("03", "08-probe", "Y2"))
        self.assertNotEqual(first, stable_repair_r7_seed("15", "08-probe", "Y1"))


if __name__ == "__main__":
    unittest.main()
