import json,unittest
from pathlib import Path
from apply_2002_cast import apply_cast_to_doc
ROOT=Path(__file__).resolve().parents[2]
class ApplyCastTests(unittest.TestCase):
    def test_all_six_primary_actors_are_content_selected_and_distinct(self):
        cast=json.loads((ROOT/'voice-pipeline/config/cast_2002.json').read_text())
        expected={'cloze':'04','text1':'05','text2':'08','text3':'01','text4':'09','translation':'02'}
        self.assertEqual({k:v['primary_actor_id'] for k,v in cast['articles'].items()},expected)
        self.assertEqual(len(set(expected.values())),6)
    def test_overlay_replaces_narrator_but_preserves_explicit_roles_and_zeroes_pauses(self):
        cast=json.loads((ROOT/'voice-pipeline/config/cast_2002.json').read_text())
        doc={'article_id':'text2','article':{'background':'old'},'sentences':[{'segments':[{'speaker_role':'narrator','actor_id':'05','pause_before_ms':9,'pause_after_ms':80},{'speaker_role':'dave_lavery','actor_id':'12','pause_before_ms':0,'pause_after_ms':20}]}]}
        out=apply_cast_to_doc(doc,cast);segs=out['sentences'][0]['segments']
        self.assertEqual(out['primary_actor_id'],'08');self.assertEqual(segs[0]['actor_id'],'08');self.assertEqual(segs[1]['actor_id'],'01')
        self.assertTrue(all(s['pause_before_ms']==s['pause_after_ms']==0 for s in segs))
        self.assertNotEqual(out['article']['background'],'old')
if __name__=='__main__':unittest.main()
