import unittest
from generate_2002_v2 import performance_controls, build_cues

class Generate2002V2Tests(unittest.TestCase):
    def test_emotion_controls_are_audibly_separated_without_post_tempo(self):
        neutral=performance_controls({'emotion':'neutral','intensity':1})
        lively=performance_controls({'emotion':'lively','intensity':1})
        ironic=performance_controls({'emotion':'ironic','intensity':2})
        self.assertFalse(neutral['post_tempo'])
        self.assertEqual(neutral['artificial_pause_ms'],0)
        self.assertGreater(lively['exaggeration']-neutral['exaggeration'],0.15)
        self.assertGreater(ironic['exaggeration']-neutral['exaggeration'],0.25)
        self.assertLess(ironic['cfg_weight'],neutral['cfg_weight'])

    def test_build_cues_creates_one_continuous_zero_gap_timeline(self):
        segments=[
            {'id':'a','text':'hello ','emotion':'neutral','intensity':1,'duration_seconds':1.25},
            {'id':'b','text':'world','emotion':'warm','intensity':1,'duration_seconds':2.0},
        ]
        cues=build_cues(segments)
        self.assertEqual(cues[0]['start'],0)
        self.assertEqual(cues[0]['end'],1.25)
        self.assertEqual(cues[1]['start'],1.25)
        self.assertEqual(cues[1]['end'],3.25)
        self.assertEqual(cues[0]['text'],'hello ')

if __name__=='__main__':
    unittest.main()
