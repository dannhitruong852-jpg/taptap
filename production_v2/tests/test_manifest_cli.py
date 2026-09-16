import json
import tempfile
import unittest
from pathlib import Path

from production_v2.cli_manifest import main


class ManifestCliTests(unittest.TestCase):
    def test_create_validate_and_advance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / 'batch.json'
            self.assertEqual(main([
                'create', '--batch-id', '2013-2014', '--years', '2013,2014',
                '--source-ref', 'abc', '--output', str(manifest),
            ]), 0)
            self.assertEqual(json.loads(manifest.read_text())['state'], 'draft')
            self.assertEqual(main(['validate', '--manifest', str(manifest)]), 0)

            advanced = Path(temp_dir) / 'batch2.json'
            self.assertEqual(main([
                'advance', '--manifest', str(manifest), '--to', 'validated',
                '--output', str(advanced),
            ]), 0)
            self.assertEqual(json.loads(advanced.read_text())['state'], 'validated')

    def test_illegal_advance_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / 'batch.json'
            main([
                'create', '--batch-id', 'x', '--years', '2013',
                '--source-ref', 'abc', '--output', str(manifest),
            ])
            with self.assertRaises(SystemExit):
                main([
                    'advance', '--manifest', str(manifest), '--to', 'rendering',
                    '--output', str(Path(temp_dir) / 'bad.json'),
                ])


if __name__ == '__main__':
    unittest.main()
