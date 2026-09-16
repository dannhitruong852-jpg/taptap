import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'check_2007_2012_production_ready.py'
YEARS = range(2007, 2013)
UNITS = ('cloze', 'text1', 'text2', 'text3', 'text4', 'partb', 'translation')


class ProductionReadyTests(unittest.TestCase):
    def fixture(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        freeze = root / 'reports/content-freeze'
        highlights = root / 'content-pipeline/curated/bilingual-highlights'
        highlights.mkdir(parents=True)
        freeze.mkdir(parents=True)
        (freeze / '2007-2012-production-board.json').write_text(json.dumps({
            'content_frozen': True,
            'freeze_gate_remaining': [],
        }))
        for year in YEARS:
            year_dir = freeze / str(year)
            year_dir.mkdir()
            for unit in UNITS:
                (year_dir / f'{unit}.candidate.json').write_text(json.dumps({
                    'year': year,
                    'article': {
                        'id': unit,
                        'rows': [[1, 'Body.', '正文。', 'report', []]],
                    },
                }, ensure_ascii=False))
            (year_dir / 'vocabulary-1-9.json').write_text(json.dumps({
                'year': year,
                'scale': 'project-curated-1-9-v1',
                'vocabulary': {'body': [6, '正文']},
                'qa': {'status': 'reviewed'},
            }, ensure_ascii=False))
            (highlights / f'{year}.json').write_text(json.dumps({
                'year': year,
                'articles': {'cloze': {'s01': []}},
            }))
        return td, root

    def run_checker(self, root):
        return subprocess.run([
            sys.executable, str(SCRIPT), '--root', str(root)
        ], text=True, capture_output=True, check=True)

    def test_empty_bilingual_mapping_skeleton_is_reported_as_error(self):
        td, root = self.fixture()
        self.addCleanup(td.cleanup)
        path = root / 'content-pipeline/curated/bilingual-highlights/2012.json'
        path.write_text(json.dumps({
            'year': 2012,
            'articles': {unit: {} for unit in UNITS},
            'reviewed_exceptions': [],
        }))
        result = self.run_checker(root)
        report = json.loads(result.stdout)
        self.assertIn('2012.json', report['bilingual_errors'])
        self.assertFalse(report['ready'])


if __name__ == '__main__':
    unittest.main()
