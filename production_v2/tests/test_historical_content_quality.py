import json
import unittest
from pathlib import Path

from production_v2.content_quality import validate_content_quality


class HistoricalContentQualityTests(unittest.TestCase):
    def test_real_2007_2012_frozen_content_satisfies_generic_gate(self):
        root=Path(__file__).resolve().parents[2]
        catalog_path=root/'kaoyan-reader-v1/content/catalog.json'
        evidence=root/'reports/content-freeze/2007/text1.candidate.json'
        if not catalog_path.is_file() or not evidence.is_file():
            self.skipTest('full repository historical fixtures not available in isolated unit workspace')
        catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
        manifest={'years':list(range(2007,2013))}
        report=validate_content_quality(manifest,catalog,root)
        self.assertTrue(report['ok'],json.dumps(report,ensure_ascii=False,indent=2))
        self.assertEqual(report['articles_checked'],42)
        self.assertEqual(report['reviewed_candidates_checked'],42)
        self.assertGreater(report['level6_vocab_occurrences_checked'],0)


if __name__=='__main__':
    unittest.main()
