import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'build_2007_2012_curated.py'
YEARS = range(2007, 2013)
UNITS = ('cloze', 'text1', 'text2', 'text3', 'text4', 'partb', 'translation')


class CuratedCompilerTests(unittest.TestCase):
    def fixture(self, frozen=True, omit=None):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        freeze = root / 'reports/content-freeze'
        inventory = root / 'reports/extraction/2007-2012-article-inventory.json'
        board = freeze / '2007-2012-production-board.json'
        inventory.parent.mkdir(parents=True)
        actors = {}
        years = {}
        for year in YEARS:
            y = str(year)
            actors[y] = {unit: '01' for unit in UNITS}
            years[y] = {'source_filename': f'{year}.pdf', 'source_sha256': f'sha-{year}'}
            directory = freeze / y
            directory.mkdir(parents=True)
            (directory / 'vocabulary-1-9.json').write_text(json.dumps({
                'year': year,
                'scale': 'project-curated-1-9-v1',
                'vocabulary': {'body': [6, '正文']},
                'qa': {'status': 'reviewed'},
            }, ensure_ascii=False))
            for unit in UNITS:
                if omit == (year, unit):
                    continue
                doc = {
                    'year': year,
                    'article': {
                        'id': unit,
                        'section_type': 'reading' if unit.startswith('text') else unit,
                        'title': f'{year}-{unit}',
                        'pages': [1],
                        'actor': '01',
                        'context': 'ctx',
                        'rows': [[1, f'{year} {unit} body.', '译文。', 'report', ['body']]],
                    },
                    'qa': {'source_scope_verified': True},
                }
                (directory / f'{unit}.candidate.json').write_text(json.dumps(doc, ensure_ascii=False))
        board.write_text(json.dumps({
            'content_frozen': frozen,
            'freeze_gate_remaining': [] if frozen else ['materialize_all_candidates'],
            'actor_plan': actors,
        }))
        inventory.write_text(json.dumps({'years': years}))
        return td, root

    def run_compiler(self, root):
        return subprocess.run([
            sys.executable, str(SCRIPT),
            '--root', str(root),
            '--output-dir', str(root / 'content-pipeline/curated'),
        ], text=True, capture_output=True)

    def test_refuses_unfrozen_batch(self):
        td, root = self.fixture(frozen=False)
        self.addCleanup(td.cleanup)
        result = self.run_compiler(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('content_frozen', result.stderr + result.stdout)

    def test_refuses_missing_candidate(self):
        td, root = self.fixture(frozen=True, omit=(2011, 'text3'))
        self.addCleanup(td.cleanup)
        result = self.run_compiler(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('2011/text3', result.stderr + result.stdout)

    def test_refuses_missing_vocabulary(self):
        td, root = self.fixture(frozen=True)
        self.addCleanup(td.cleanup)
        (root / 'reports/content-freeze/2010/vocabulary-1-9.json').unlink()
        result = self.run_compiler(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('2010/vocabulary-1-9.json', result.stderr + result.stdout)

    def test_compiles_six_years_without_inventing_text(self):
        td, root = self.fixture(frozen=True)
        self.addCleanup(td.cleanup)
        result = self.run_compiler(root)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        for year in YEARS:
            doc = json.loads((root / f'content-pipeline/curated/{year}.json').read_text())
            self.assertEqual(doc['year'], year)
            self.assertEqual(doc['source_sha256'], f'sha-{year}')
            self.assertEqual(len(doc['articles']), 7)
            self.assertEqual(doc['vocabulary']['body'], [6, '正文'])
            self.assertEqual(doc['articles'][0]['rows'][0][1], f'{year} cloze body.')


if __name__ == '__main__':
    unittest.main()
