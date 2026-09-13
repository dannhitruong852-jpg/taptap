import unittest

from calibration.repair_search_r6 import (
    REPAIR_R6_ACTORS,
    REPAIR_R6_TARGETS,
    REPAIR_R6_SPECS,
    build_repair_r6_profile,
    build_repair_r6_render_plan,
    total_repair_r6_renders,
)
from calibration.render_repair_auditions_r6 import stable_repair_r6_seed


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


class FinalTwoRepairRoundSixTests(unittest.TestCase):
    def test_only_final_two_curious_probe_cells_are_rendered(self):
        self.assertEqual(REPAIR_R6_ACTORS, ("03", "15"))
        self.assertEqual(REPAIR_R6_TARGETS, {"03": ("curious_probe",), "15": ("curious_probe",)})
        self.assertEqual(32, total_repair_r6_renders())

    def test_actor03_is_seed_only_at_proven_u5_control_point(self):
        spec = REPAIR_R6_SPECS["03"]["curious_probe"]
        self.assertEqual("warm", spec["reference_state"])
        self.assertEqual(
            ("If the policy appears efficient on paper, why does its burden still fall so unequally on real people?",),
            tuple(spec["synthesis_texts"]),
        )
        self.assertEqual(16, len(spec["controls"]))
        self.assertEqual({(0.42, 0.54, 0.70)}, set(spec["controls"]))

    def test_actor15_moves_to_slower_comma_region_to_raise_naturalness_proxy(self):
        spec = REPAIR_R6_SPECS["15"]["curious_probe"]
        self.assertEqual("curious", spec["reference_state"])
        self.assertEqual(
            ("If the policy appears efficient on paper, why does its burden still fall so unequally on real people?",),
            tuple(spec["synthesis_texts"]),
        )
        self.assertEqual(16, len(spec["controls"]))
        allowed = {
            (0.30, 0.64, 0.66),
            (0.29, 0.65, 0.65),
            (0.28, 0.66, 0.64),
            (0.31, 0.64, 0.65),
        }
        self.assertEqual(allowed, set(spec["controls"]))
        for ex, cfg, temp in spec["controls"]:
            self.assertLessEqual(ex, 0.31)
            self.assertGreaterEqual(cfg, 0.64)
            self.assertLessEqual(temp, 0.66)

    def test_round_six_keeps_immutable_quality_rules(self):
        for actor_id in REPAIR_R6_ACTORS:
            repaired = build_repair_r6_profile(profile(actor_id))
            renders = build_repair_r6_render_plan(repaired, SCRIPT)
            self.assertEqual(16, len(renders))
            for item in renders:
                self.assertEqual(0, item["artificial_pause_ms"])
                self.assertIs(False, item["post_tempo"])
                self.assertEqual(1.18, item["repetition_penalty"])
                self.assertEqual("curious_probe", item["intent"])
                self.assertTrue(item["variant"].startswith("X"))

    def test_round_six_seed_is_deterministic_and_actor_specific(self):
        first = stable_repair_r6_seed("03", "08-probe", "X1")
        self.assertEqual(first, stable_repair_r6_seed("03", "08-probe", "X1"))
        self.assertNotEqual(first, stable_repair_r6_seed("03", "08-probe", "X2"))
        self.assertNotEqual(first, stable_repair_r6_seed("15", "08-probe", "X1"))


if __name__ == "__main__":
    unittest.main()
