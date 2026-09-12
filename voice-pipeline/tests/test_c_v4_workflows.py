import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


class C4WorkflowContractTests(unittest.TestCase):
    def setUp(self):
        self.generate=ROOT/'.github/workflows/generate-c-v4.yml'
        self.verify=ROOT/'.github/workflows/verify-c-v4-reader.yml'

    def test_generate_workflow_is_generic_year_aware_candidate_pipeline(self):
        self.assertTrue(self.generate.is_file(),'generate-c-v4.yml missing')
        text=self.generate.read_text(encoding='utf-8')
        self.assertRegex(text,r'workflow_dispatch:[\s\S]*inputs:[\s\S]*year:')
        self.assertIn('article: [cloze, text1, text2, text3, text4, translation]',text)
        self.assertIn('shard: [0, 1, 2]',text)
        self.assertIn('generate_c_v4.py --year',text)
        self.assertIn('merge_c_v4.py --year',text)
        self.assertIn('verify_c_v4.py --year',text)
        self.assertIn('torch==2.7.1',text)
        self.assertIn('torchaudio==2.7.1',text)
        self.assertLess(text.index('merge_c_v4.py --year'),text.index('align_manifests.py --year'))
        self.assertIn('audioVersion=v4',text)
        self.assertIn('2002-c-v4-candidate',text)
        self.assertNotIn('git push origin HEAD:kaoyan-reader-v1',text)

    def test_public_verify_requires_all_six_manifests_and_word_timestamps(self):
        self.assertTrue(self.verify.is_file(),'verify-c-v4-reader.yml missing')
        text=self.verify.read_text(encoding='utf-8')
        self.assertRegex(text,r'workflow_dispatch:[\s\S]*inputs:[\s\S]*year:')
        self.assertIn("['cloze','text1','text2','text3','text4','translation']",text)
        self.assertIn('assert total==91',text)
        self.assertIn("alignment_status']=='passed'",text)
        self.assertIn("qa']['voice']=='pending'",text)
        self.assertIn("qa']['c_direction']=='pending'",text)
        self.assertIn('READER_AUDIO_VERSION: v4',text)
        self.assertIn('reader-ux-browser.py',text)


if __name__ == '__main__':
    unittest.main()
