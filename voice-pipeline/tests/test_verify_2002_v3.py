import tempfile,unittest,json
from pathlib import Path
try:
    from verify_2002_v3 import verify_article_manifest
except Exception:
    verify_article_manifest=None
class VerifyV3Tests(unittest.TestCase):
    def test_rejects_wrong_version_and_missing_sentence(self):
        self.assertTrue(callable(verify_article_manifest),'v3 verifier missing')
        content={'article_id':'x','sentences':[{'id':'s01','segments':[{'actor_id':'01'}]}]}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);m=root/'manifest.json'
            m.write_text(json.dumps({'c_mode_version':'old','sentences':{}}))
            result=verify_article_manifest(content,m,decode=False)
            self.assertFalse(result['complete'])
            self.assertIn('wrong_c_mode_version',result['errors'])
            self.assertIn('missing_sentence:s01',result['errors'])
if __name__=='__main__':unittest.main()
