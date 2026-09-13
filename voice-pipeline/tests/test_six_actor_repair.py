import unittest

from calibration.repair_search import REPAIR_ACTORS, REPAIR_TARGETS, build_repair_render_plan
from calibration.render_repair_auditions import stable_repair_seed
from calibration.repair_search_r2 import (
    REPAIR_R2_ACTORS,
    REPAIR_R2_TARGETS,
    REPAIR_R2_SPECS,
    build_repair_r2_profile,
    build_repair_r2_render_plan,
    total_repair_r2_renders,
)


SCRIPT = {
    "scenes": [
        {"id": "01-explanation", "intent": "neutral_explain", "intensity": 1, "category": "explanation", "text": "Neutral text."},
        {"id": "04-story", "intent": "narrative_build", "intensity": 1, "category": "story", "text": "Narrative text."},
        {"id": "06-emphasis", "intent": "information_peak", "intensity": 2, "category": "emphasis", "text": "Important information."},
        {"id": "07-humor", "intent": "restrained_irony", "intensity": 1, "category": "humor", "text": "Restrained irony."},
        {"id": "08-probe", "intent": "curious_probe", "intensity": 1, "category": "probe", "text": "A curious question."},
        {"id": "10-long-sentence", "intent": "qualification", "intensity": 1, "category": "qualification", "text": "A qualified statement."},
    ]
}


def profile(actor_id):
    refs = {state: f"actor{actor_id}-{state}.wav" for state in (
        "neutral", "warm", "lively", "serious", "curious", "ironic", "tense", "emotional"
    )}
    intents = {}
    for scene in SCRIPT["scenes"]:
        intents[scene["intent"]] = {
            "reference_state": "neutral",
            "center": {
                "exaggeration": 0.5,
                "cfg_weight": 0.5,
                "temperature": 0.75,
                "repetition_penalty": 1.18,
            },
        }
    return {
        "actor_id": actor_id,
        "calibration_id": f"actor-{actor_id}-audition-v1",
        "references": refs,
        "intent_profiles": intents,
        "eligible": False,
        "eligible_for": [],
        "selected_candidates": {},
    }


class SixActorRepairTests(unittest.TestCase):
    def test_targets_only_the_six_failed_actors_and_fourteen_failed_intents(self):
        self.assertEqual(REPAIR_ACTORS, ("03", "07", "10", "11", "14", "15"))
        self.assertEqual(
            REPAIR_TARGETS,
            {
                "03": ("curious_probe",),
                "07": ("curious_probe",),
                "10": ("information_peak", "curious_probe"),
                "11": ("restrained_irony", "curious_probe"),
                "14": ("information_peak", "restrained_irony", "qualification", "curious_probe"),
                "15": ("narrative_build", "information_peak", "qualification", "curious_probe"),
            },
        )
        self.assertNotIn("06", REPAIR_ACTORS)
        self.assertEqual(14, sum(len(v) for v in REPAIR_TARGETS.values()))

    def test_repair_plan_never_lowers_qa_or_uses_post_processing(self):
        for actor_id in REPAIR_ACTORS:
            renders = build_repair_render_plan(profile(actor_id), SCRIPT)
            self.assertTrue(renders)
            self.assertEqual(set(REPAIR_TARGETS[actor_id]), {item["intent"] for item in renders})
            for item in renders:
                self.assertEqual(actor_id, item["actor_id"])
                self.assertEqual(0, item["artificial_pause_ms"])
                self.assertIs(False, item["post_tempo"])
                self.assertEqual(1.18, item["repetition_penalty"])
                self.assertTrue(item["variant"].startswith("R"))
                self.assertIn(item["reference_state"], profile(actor_id)["references"])
                self.assertEqual(profile(actor_id)["references"][item["reference_state"]], item["reference"])

    def test_round_one_is_bounded_to_57_targeted_renders(self):
        total = sum(len(build_repair_render_plan(profile(actor), SCRIPT)) for actor in REPAIR_ACTORS)
        self.assertEqual(57, total)

    def test_actor15_uses_clarity_first_search_for_systematic_asr_and_pace_failures(self):
        renders = build_repair_render_plan(profile("15"), SCRIPT)
        by_intent = {}
        for item in renders:
            by_intent.setdefault(item["intent"], []).append(item)
        narrative = by_intent["narrative_build"]
        self.assertEqual(4, len(narrative))
        self.assertTrue(all(item["temperature"] <= 0.76 for item in narrative))
        self.assertTrue(all(item["cfg_weight"] >= 0.46 for item in narrative))
        self.assertTrue(all(item["exaggeration"] <= 0.50 for item in narrative))
        info = by_intent["information_peak"]
        self.assertEqual(5, len(info))
        self.assertLessEqual(min(item["temperature"] for item in info), 0.72)
        self.assertGreaterEqual(max(item["cfg_weight"] for item in info), 0.52)

    def test_actor14_speed_repairs_include_neutral_reference_without_touching_global_standard(self):
        renders = build_repair_render_plan(profile("14"), SCRIPT)
        by_intent = {}
        for item in renders:
            by_intent.setdefault(item["intent"], []).append(item)
        for intent in ("information_peak", "restrained_irony", "qualification", "curious_probe"):
            self.assertIn("neutral", {item["reference_state"] for item in by_intent[intent]})

    def test_repair_seed_is_deterministic_and_separate_from_original_audition_seed_space(self):
        first = stable_repair_seed("03", "08-probe", "R1")
        self.assertEqual(first, stable_repair_seed("03", "08-probe", "R1"))
        self.assertNotEqual(first, stable_repair_seed("03", "08-probe", "R2"))
        self.assertNotEqual(first, stable_repair_seed("07", "08-probe", "R1"))


class SixActorRepairRoundTwoTests(unittest.TestCase):
    def test_round_two_targets_only_remaining_failed_cells(self):
        self.assertEqual(REPAIR_R2_ACTORS, ("03", "07", "14", "15"))
        self.assertEqual(
            REPAIR_R2_TARGETS,
            {
                "03": ("curious_probe",),
                "07": ("curious_probe",),
                "14": ("information_peak", "restrained_irony"),
                "15": ("narrative_build", "curious_probe"),
            },
        )
        self.assertEqual(6, sum(len(v) for v in REPAIR_R2_TARGETS.values()))
        self.assertEqual(50, total_repair_r2_renders())

    def test_round_two_keeps_the_same_immutable_rules(self):
        for actor_id in REPAIR_R2_ACTORS:
            repaired_profile = build_repair_r2_profile(profile(actor_id))
            renders = build_repair_r2_render_plan(repaired_profile, SCRIPT)
            self.assertEqual(set(REPAIR_R2_TARGETS[actor_id]), {item["intent"] for item in renders})
            for item in renders:
                self.assertEqual(0, item["artificial_pause_ms"])
                self.assertIs(False, item["post_tempo"])
                self.assertEqual(1.18, item["repetition_penalty"])
                self.assertTrue(item["variant"].startswith("S"))
                local = repaired_profile["intent_profiles"][item["intent"]]
                self.assertEqual(local["reference_state"], item["reference_state"])
                self.assertEqual(repaired_profile["references"][item["reference_state"]], item["reference"])

    def test_round_two_uses_actor_specific_reference_diagnosis(self):
        expected = {
            ("03", "curious_probe"): "ironic",
            ("07", "curious_probe"): "lively",
            ("14", "information_peak"): "emotional",
            ("14", "restrained_irony"): "emotional",
            ("15", "narrative_build"): "neutral",
            ("15", "curious_probe"): "curious",
        }
        for (actor, intent), reference in expected.items():
            self.assertEqual(reference, REPAIR_R2_SPECS[actor][intent]["reference_state"])

    def test_actor15_round_two_is_seed_dense_near_the_best_round_one_regions(self):
        repaired = build_repair_r2_profile(profile("15"))
        renders = build_repair_r2_render_plan(repaired, SCRIPT)
        by_intent = {}
        for item in renders:
            by_intent.setdefault(item["intent"], []).append(item)
        narrative = by_intent["narrative_build"]
        probe = by_intent["curious_probe"]
        self.assertEqual(10, len(narrative))
        self.assertEqual(8, len(probe))
        self.assertTrue(all(item["temperature"] <= 0.72 for item in narrative))
        self.assertTrue(all(item["temperature"] <= 0.70 for item in probe))
        self.assertTrue(all(item["cfg_weight"] >= 0.57 for item in probe))
        self.assertTrue(all(item["exaggeration"] <= 0.40 for item in probe))


if __name__ == "__main__":
    unittest.main()
