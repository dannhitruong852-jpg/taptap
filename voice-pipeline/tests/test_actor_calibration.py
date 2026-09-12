import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CALIBRATION = ROOT / "voice-pipeline" / "calibration"
ACTORS = ("01", "02", "04", "05", "08", "09", "12", "13")


def load_module(name):
    path = CALIBRATION / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ActorCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grid = load_module("candidate_grid")
        cls.renderer = load_module("render_auditions")
        cls.board = load_module("build_audition_board")

    def test_common_battery_covers_ten_required_scenes(self):
        script = json.loads((CALIBRATION / "audition_script.json").read_text())
        self.assertEqual(len(script["scenes"]), 10)
        self.assertEqual(
            {scene["category"] for scene in script["scenes"]},
            {
                "ordinary_explanation", "rational_analysis", "warm_conversation",
                "story_setup", "turn", "information_emphasis", "restrained_humor",
                "serious_commentary", "quotation_role", "long_complex_sentence",
            },
        )
        self.assertTrue(all(scene["text"].strip() for scene in script["scenes"]))

    def test_eight_profiles_are_independent_and_ineligible(self):
        profiles = []
        for actor_id in ACTORS:
            path = CALIBRATION / "actors" / f"{actor_id}.json"
            profile = json.loads(path.read_text())
            profiles.append(profile)
            self.assertEqual(profile["actor_id"], actor_id)
            self.assertFalse(profile["eligible"])
            self.assertEqual(profile["human_listening_qa"]["status"], "pending")
            self.assertEqual(profile["selected_candidates"], {})
            self.assertIn(f"actor{actor_id}-", profile["references"]["neutral"])
        self.assertEqual(len({p["source_speaker"] for p in profiles}), len(ACTORS))
        self.assertEqual(len({p["calibration_id"] for p in profiles}), len(ACTORS))

    def test_every_scene_has_actor_bounded_abc_candidates(self):
        script = json.loads((CALIBRATION / "audition_script.json").read_text())
        for actor_id in ACTORS:
            profile = json.loads((CALIBRATION / "actors" / f"{actor_id}.json").read_text())
            for scene in script["scenes"]:
                candidates = self.grid.candidate_controls(profile, scene["intent"], scene["intensity"])
                self.assertEqual([c["variant"] for c in candidates], ["A", "B", "C"])
                self.assertEqual([c["delivery"] for c in candidates], ["restrained", "balanced", "expressive"])
                for candidate in candidates:
                    bounds = profile["intent_profiles"][scene["intent"]]["bounds"]
                    self.assertLessEqual(bounds["exaggeration"][0], candidate["exaggeration"])
                    self.assertLessEqual(candidate["exaggeration"], bounds["exaggeration"][1])
                    self.assertLessEqual(bounds["cfg_weight"][0], candidate["cfg_weight"])
                    self.assertLessEqual(candidate["cfg_weight"], bounds["cfg_weight"][1])
                    self.assertEqual(candidate["artificial_pause_ms"], 0)
                    self.assertFalse(candidate["post_tempo"])

    def test_actor_profiles_do_not_collapse_to_a_global_grid(self):
        p01 = json.loads((CALIBRATION / "actors" / "01.json").read_text())
        p08 = json.loads((CALIBRATION / "actors" / "08.json").read_text())
        self.assertNotEqual(
            self.grid.candidate_controls(p01, "curious_probe", 1),
            self.grid.candidate_controls(p08, "curious_probe", 1),
        )

    def test_render_plan_uses_own_actor_references_and_deterministic_seeds(self):
        profile = json.loads((CALIBRATION / "actors" / "05.json").read_text())
        script = json.loads((CALIBRATION / "audition_script.json").read_text())
        first = self.renderer.build_render_plan(profile, script)
        second = self.renderer.build_render_plan(profile, script)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 30)
        self.assertTrue(all(item["reference"].startswith("actor05-") for item in first))
        self.assertTrue(all(item["artificial_pause_ms"] == 0 for item in first))
        self.assertTrue(all(item["post_tempo"] is False for item in first))

    def test_board_labels_benchmark_without_approving_any_actor(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifests = root / "manifests"
            manifests.mkdir()
            (manifests / "05.json").write_text(json.dumps({"actor_id": "05", "renders": []}))
            output = root / "board"
            self.board.build_board(manifests, output)
            html = (output / "index.html").read_text()
            data = json.loads((output / "auditions.json").read_text())
            self.assertIn("Actor 05 / Text 1 human-naturalness benchmark", html)
            self.assertNotIn("eligible: true", html.lower())
            self.assertEqual(data["human_voice_qa"], "pending")


if __name__ == "__main__":
    unittest.main()
