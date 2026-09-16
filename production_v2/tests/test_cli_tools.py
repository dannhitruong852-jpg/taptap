import json
import tempfile
import unittest
from pathlib import Path

from production_v2.cli_matrix import main as matrix_main
from production_v2.cli_release_guard import main as release_main


class CliToolsTests(unittest.TestCase):
    def test_release_guard_cli_blocks_regression(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old = root / 'old.json'
            new = root / 'new.json'
            report = root / 'report.json'
            old.write_text(json.dumps({'articles': [{'id': '2003-text1', 'year': 2003}]}))
            new.write_text(json.dumps({'articles': []}))
            self.assertEqual(release_main([
                '--old', str(old), '--new', str(new), '--report', str(report),
            ]), 2)
            self.assertFalse(json.loads(report.read_text())['ok'])

    def test_matrix_cli_writes_matrix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / 'manifest.json'
            catalog = root / 'catalog.json'
            output = root / 'matrix.json'
            manifest.write_text(json.dumps({'years': [2013]}))
            catalog.write_text(json.dumps({
                'articles': [{'id': '2013-text1', 'year': 2013}],
            }))
            self.assertEqual(matrix_main([
                '--manifest', str(manifest), '--catalog', str(catalog),
                '--shards', '2', '--output', str(output),
            ]), 0)
            self.assertEqual(len(json.loads(output.read_text())['include']), 2)


if __name__ == '__main__':
    unittest.main()
