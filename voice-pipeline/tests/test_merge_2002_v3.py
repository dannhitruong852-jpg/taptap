import unittest
try:
    from merge_2002_v3 import ARTICLES, version_summary
except Exception:
    ARTICLES=None; version_summary=None
class Merge2002V3Tests(unittest.TestCase):
    def test_merge_covers_all_six_units(self):
        self.assertEqual(ARTICLES,('cloze','text1','text2','text3','text4','translation'))
    def test_summary_marks_content_cast_v3(self):
        self.assertEqual(version_summary()['version'],'2002-c-v3-content-cast')
        self.assertEqual(version_summary()['artificial_pause_ms'],0)
        self.assertFalse(version_summary()['post_tempo'])
if __name__=='__main__':unittest.main()
