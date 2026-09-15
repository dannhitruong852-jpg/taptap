import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import merge_c_v4


class GenericMergeTests(unittest.TestCase):
    def test_merge_status_uses_discovered_required_articles(self):
        required = {'cloze', 'text1', 'translation'}
        articles = {name: {'missing': [], 'sentences': 2} for name in required}
        self.assertEqual(merge_c_v4.merge_status(required, articles), 'complete_candidate')
        del articles['translation']
        self.assertEqual(merge_c_v4.merge_status(required, articles), 'partial_candidate')

    def test_collect_segments_accepts_new_items_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            d = root / 'artifact'; d.mkdir()
            opus = d / 'v4-s01-01.opus'; mp3 = d / 'v4-s01-01.mp3'
            opus.write_bytes(b'opus'); mp3.write_bytes(b'mp3')
            entry = {
                'status': 'ok', 'generation_fingerprint': 'g',
                'files': {opus.name: merge_c_v4.sha(opus), mp3.name: merge_c_v4.sha(mp3)},
            }
            (d / 'v4-shard-0.json').write_text(json.dumps({'article':'text1','items':{'s01-01':entry}}))
            found = merge_c_v4._collect_segments(root, 'text1')
            self.assertIn('s01-01', found)

    def test_discover_articles_is_year_generic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); p = root / 'content/2005/c'; p.mkdir(parents=True)
            for name in ('translation', 'text2', 'cloze'):
                (p / f'{name}.json').write_text('{}')
            self.assertEqual(merge_c_v4.discover_articles(root, 2005), ['cloze', 'text2', 'translation'])


if __name__ == '__main__':
    unittest.main()
