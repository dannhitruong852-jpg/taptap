import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from production_v2.cli_content_quality import main


class ContentQualityCliTests(unittest.TestCase):
    @patch('production_v2.cli_content_quality.validate_content_quality')
    def test_exit_zero_on_pass_and_writes_report(self, validate):
        validate.return_value={'ok':True,'errors':[]}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); manifest=root/'m.json'; catalog=root/'c.json'; report=root/'r.json'
            manifest.write_text(json.dumps({'years':[2013]})); catalog.write_text(json.dumps({'articles':[]}))
            self.assertEqual(main(['--manifest',str(manifest),'--catalog',str(catalog),'--root',str(root),'--report',str(report)]),0)
            self.assertTrue(json.loads(report.read_text())['ok'])

    @patch('production_v2.cli_content_quality.validate_content_quality')
    def test_exit_two_on_quality_failure(self, validate):
        validate.return_value={'ok':False,'errors':['bad']}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); manifest=root/'m.json'; catalog=root/'c.json'; report=root/'r.json'
            manifest.write_text(json.dumps({'years':[2013]})); catalog.write_text(json.dumps({'articles':[]}))
            self.assertEqual(main(['--manifest',str(manifest),'--catalog',str(catalog),'--root',str(root),'--report',str(report)]),2)


if __name__=='__main__':
    unittest.main()
