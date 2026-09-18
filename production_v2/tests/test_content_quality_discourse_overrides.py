import json
import tempfile
import unittest
from pathlib import Path

from production_v2.content_quality import validate_content_quality
from test_content_quality import ContentQualityTests, article_doc, candidate


class ContentQualityDiscourseOverrideTests(unittest.TestCase):
    def test_reviewed_discourse_sidecar_is_applied_before_quality_comparison(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            labels = ('report', 'report', 'report')
            compiled = article_doc(discourse=('report', 'contrast', 'report'))
            helper = ContentQualityTests()
            batch, catalog = helper._write(td, cand=candidate(discourse=labels), doc=compiled)

            override_dir = root / 'content-pipeline/curated/discourse-overrides'
            override_dir.mkdir(parents=True, exist_ok=True)
            (override_dir / '2013.json').write_text(json.dumps({
                'year': 2013,
                'overrides': [{
                    'article_id': 'text1',
                    'sentence_id': 's02',
                    'from': 'report',
                    'to': 'contrast',
                    'reason': 'Reviewed explicit contrast.',
                }],
            }), encoding='utf-8')

            report = validate_content_quality(batch, catalog, root)
            self.assertTrue(report['ok'], report)


if __name__ == '__main__':
    unittest.main()
