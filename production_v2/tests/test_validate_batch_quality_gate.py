import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from production_v2.cli_validate_batch import main


class ValidateBatchQualityGateTests(unittest.TestCase):
    def _files(self, root):
        root=Path(root)
        manifest=root/'m.json'; catalog=root/'c.json'; reader=root/'kaoyan-reader-v1'; report=root/'r.json'
        manifest.write_text(json.dumps({'batch_id':'b','pipeline_version':2,'years':[2013],'expected_articles':{'2013':['text1']},'source_ref':'abc','state':'validated','created_at':'x'}))
        catalog.write_text(json.dumps({'articles':[]}))
        reader.mkdir()
        return manifest,catalog,reader,report

    @patch('production_v2.cli_validate_batch.validate_content_quality')
    @patch('production_v2.cli_validate_batch.validate_batch')
    def test_preflight_runs_generic_content_quality_gate(self, structural, quality):
        structural.return_value={'ok':True,'errors':[]}
        quality.return_value={'ok':False,'errors':['scope bad']}
        with tempfile.TemporaryDirectory() as td:
            m,c,r,out=self._files(td)
            code=main(['--manifest',str(m),'--catalog',str(c),'--reader-root',str(r),'--phase','preflight','--report',str(out)])
            self.assertEqual(code,2)
            quality.assert_called_once()
            doc=json.loads(out.read_text())
            self.assertFalse(doc['ok'])
            self.assertIn('scope bad',doc['errors'])

    @patch('production_v2.cli_validate_batch.validate_content_quality')
    @patch('production_v2.cli_validate_batch.validate_batch')
    def test_release_does_not_require_review_evidence_in_production_tree(self, structural, quality):
        structural.return_value={'ok':True,'errors':[]}
        with tempfile.TemporaryDirectory() as td:
            m,c,r,out=self._files(td)
            code=main(['--manifest',str(m),'--catalog',str(c),'--reader-root',str(r),'--phase','release','--report',str(out)])
            self.assertEqual(code,0)
            quality.assert_not_called()


if __name__=='__main__':
    unittest.main()
