import json
import unittest
from pathlib import Path

from calibration.article_preview import build_article_render_plan


class ArticlePreviewTest(unittest.TestCase):
    def test_builds_one_five_segment_plan_for_each_of_15_actors(self):
        root = Path(__file__).resolve().parents[2]
        script = json.loads((root / "voice-pipeline/calibration/article_emotion_probe.json").read_text(encoding="utf-8"))
        profiles = root / "voice-pipeline/calibration/actors"
        plans = build_article_render_plan(profiles, script)

        self.assertEqual(sorted(plans), [f"{i:02d}" for i in range(1, 16)])
        self.assertTrue(all(len(items) == 5 for items in plans.values()))
        self.assertTrue(all(item["artificial_pause_ms"] == 0 for items in plans.values() for item in items))
        self.assertTrue(all(item["post_tempo"] is False for items in plans.values() for item in items))


if __name__ == "__main__":
    unittest.main()
