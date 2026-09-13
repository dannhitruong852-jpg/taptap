import unittest

from calibration.repair_search import REPAIR_ACTORS, REPAIR_TARGETS, build_repair_render_plan


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
    return {
        "actor_id": actor_id,
        "calibration_id": f"actor-{actor_id}-audition-v1",
        "references": refs,
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


if __name__ == "__main__":
    unittest.main()
