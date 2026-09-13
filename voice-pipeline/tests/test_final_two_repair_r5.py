import unittest

from calibration.repair_search_r5 import (
    REPAIR_R5_ACTORS,
    REPAIR_R5_TARGETS,
    REPAIR_R5_SPECS,
    build_repair_r5_profile,
    build_repair_r5_render_plan,
    total_repair_r5_renders,
)
from calibration.render_repair_auditions_r5 import stable_repair_r5_seed


SCRIPT = {
    "scenes": [
        {
            "id": "08-probe",
            "intent": "curious_probe",
            "intensity": 1,
            "category": "probe",
            "text": "If the policy appears efficient on paper, why does its burden still fall so unequally on real people?",
        }
    ]
}


def profile(actor_id):
    refs = {state: f"actor{actor_id}-{state}.wav" for state in (
        "neutral", "warm", "lively", "serious", "curious", "ironic", "tense", "emotional"
    )}
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


class FinalTwoRepairRoundFiveTests(unittest.TestCase):
    def test_only_03_and_15_curious_probe_remain(self):
        self.assertEqual(REPAIR_R5_ACTORS, ("03", "15"))
        self.assertEqual(REPAIR_R5_TARGETS, {"03": ("curious_probe",), "15": ("curious_probe",)})
        self.assertEqual(32, total_repair_r5_renders())

    def test_actor03_is_localized_around_u5_and_removes_punctuation_pause_as_one_axis(self):
        spec = REPAIR_R5_SPECS["03"]["curious_probe"]
        self.assertEqual("warm", spec["reference_state"])
        self.assertEqual(2, len(spec["synthesis_texts"]))
        self.assertIn(
            "If the policy appears efficient on paper why does its burden still fall so unequally on real people?",
            spec["synthesis_texts"],
        )
        self.assertEqual(8, len(spec["controls"]))
        self.assertTrue(all(0.40 <= ex <= 0.44 for ex, _, _ in spec["controls"]))
        self.assertTrue(all(0.52 <= cfg <= 0.55 for _, cfg, _ in spec["controls"]))
        self.assertTrue(all(0.69 <= temp <= 0.72 for _, _, temp in spec["controls"]))

    def test_actor15_is_seed_dense_around_v31_naturalness_region(self):
        spec = REPAIR_R5_SPECS["15"]["curious_probe"]
        self.assertEqual("curious", spec["reference_state"])
        self.assertEqual(
            ("If the policy appears efficient on paper; why does its burden still fall so unequally on real people?",),
            tuple(spec["synthesis_texts"]),
        )
        self.assertEqual(16, len(spec["controls"]))
        self.assertTrue(all(0.30 <= ex <= 0.36 for ex, _, _ in spec["controls"]))
        self.assertTrue(all(0.58 <= cfg <= 0.64 for _, cfg, _ in spec["controls"]))
        self.assertTrue(all(0.66 <= temp <= 0.69 for _, _, temp in spec["controls"]))

    def test_round_five_keeps_qa2_immutable_rules(self):
        for actor_id in REPAIR_R5_ACTORS:
            repaired = build_repair_r5_profile(profile(actor_id))
            renders = build_repair_r5_render_plan(repaired, SCRIPT)
            self.assertEqual(16, len(renders))
            for item in renders:
                self.assertEqual(0, item["artificial_pause_ms"])
                self.assertIs(False, item["post_tempo"])
                self.assertEqual(1.18, item["repetition_penalty"])
                self.assertTrue(item["variant"].startswith("W"))
                self.assertEqual("curious_probe", item["intent"])

    def test_round_five_seed_is_deterministic_and_actor_specific(self):
        first = stable_repair_r5_seed("03", "08-probe", "W1")
        self.assertEqual(first, stable_repair_r5_seed("03", "08-probe", "W1"))
        self.assertNotEqual(first, stable_repair_r5_seed("03", "08-probe", "W2"))
        self.assertNotEqual(first, stable_repair_r5_seed("15", "08-probe", "W1"))


if __name__ == "__main__":
    unittest.main()
