import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATE = ROOT / '.github/workflows/generate-kaoyan-2007-2012-batch.yml'
PUBLISH = ROOT / '.github/workflows/publish-kaoyan-2007-2012-batch.yml'
YEARS = tuple(range(2007, 2013))
UNITS = ('cloze', 'text1', 'text2', 'text3', 'text4', 'partb', 'translation')


class WorkflowContractTests(unittest.TestCase):
    def test_generate_workflow_is_freeze_gated_and_covers_full_batch(self):
        self.assertTrue(GENERATE.is_file(), f'missing {GENERATE.relative_to(ROOT)}')
        text = GENERATE.read_text()
        self.assertIn('python scripts/build_2007_2012_curated.py', text)
        self.assertIn('needs: [preflight, voicepack]', text)
        self.assertIn('shard: [0, 1, 2]', text)
        for year in YEARS:
            self.assertIn(f'year: {year}', text)
        for unit in UNITS:
            self.assertIn(f'article: {unit}', text)
        self.assertIn('year: [2007, 2008, 2009, 2010, 2011, 2012]', text)

    def test_publish_workflow_requires_generate_run_and_all_six_years(self):
        self.assertTrue(PUBLISH.is_file(), f'missing {PUBLISH.relative_to(ROOT)}')
        text = PUBLISH.read_text()
        self.assertIn('generate_run_id:', text)
        self.assertIn('actions/download-artifact@v4', text)
        self.assertIn('Reader tests', text)
        self.assertIn('Publish generated batch', text)
        for year in YEARS:
            self.assertIn(str(year), text)
        self.assertIn("expected={year:7 for year in range(2007,2013)}", text)


if __name__ == '__main__':
    unittest.main()
