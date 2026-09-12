import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
try:
    from generate_2002_v3 import ARTICLES, performance_controls, reference_filename
except Exception:
    ARTICLES=None; performance_controls=None; reference_filename=None

class Generate2002V3Tests(unittest.TestCase):
    def test_all_six_articles_are_supported(self):
        self.assertEqual(ARTICLES,('cloze','text1','text2','text3','text4','translation'))
    def test_reference_filename_binds_actor_and_emotion(self):
        self.assertEqual(reference_filename({'actor_id':'08','emotion':'ironic'}),'actor08-ironic.wav')
        self.assertEqual(reference_filename({'actor_id':'02','emotion':'neutral'}),'actor02-neutral.wav')
    def test_no_artificial_pause_or_post_tempo(self):
        controls=performance_controls({'emotion':'serious','intensity':2})
        self.assertEqual(controls['artificial_pause_ms'],0)
        self.assertFalse(controls['post_tempo'])
        self.assertGreaterEqual(controls['exaggeration'],.64)
    def test_content_actor_ids_are_materialized_by_cast_config(self):
        cfg=json.loads((ROOT/'voice-pipeline/config/cast_2002.json').read_text())
        available=set(cfg['actors'])
        for article in ('cloze','text1','text2','text3','text4','translation'):
            doc=json.loads((ROOT/f'kaoyan-reader-v1/content/2002/c/{article}.json').read_text())
            for row in doc['sentences']:
                for seg in row['segments']:
                    self.assertIn(seg['actor_id'],available,(article,seg['id'],seg['actor_id']))
if __name__=='__main__':unittest.main()
