import tempfile
import unittest
from pathlib import Path

from production_v2.freeze import build_freeze_report


class FreezeTests(unittest.TestCase):
    def test_freeze_report_hashes_selected_content_deterministically(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / 'content/2013/c/text1.json'
            target.parent.mkdir(parents=True)
            target.write_text('{"sentences":[]}')

            catalog = {'articles': [
                {'id': '2013-text1', 'year': 2013, 'content': './content/2013/c/text1.json'},
            ]}
            manifest = {
                'batch_id': 'b',
                'pipeline_version': 2,
                'years': [2013],
                'source_ref': 'abc',
            }

            first = build_freeze_report(manifest, catalog, root)
            second = build_freeze_report(manifest, catalog, root)
            self.assertEqual(first['freeze_id'], second['freeze_id'])
            self.assertEqual(first['article_count'], 1)
            self.assertEqual(len(first['articles']['2013-text1']['content_sha256']), 64)


if __name__ == '__main__':
    unittest.main()
