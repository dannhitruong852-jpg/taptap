import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from build_c_v4_voice_plan import build_voice_plan


class VoicePlanTests(unittest.TestCase):
    def test_compiles_director_intent_through_actor_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            calibration = root / 'calibration'
            calibration.mkdir()
            profile = {
                'calibration_id':'actor-05-audition-v1','actor_id':'05','eligible':True,
                'references':{'neutral':'actor05-neutral.wav'},
                'intent_profiles':{'neutral_explain':{
                    'reference_state':'neutral',
                    'center':{'exaggeration':.5,'cfg_weight':.4,'temperature':.8,'repetition_penalty':1.18},
                    'step':{'exaggeration':.08,'cfg_weight':-.035,'temperature':.025},
                    'intensity_shift':{'exaggeration':.025,'cfg_weight':-.015},
                    'bounds':{'exaggeration':[.25,.85],'cfg_weight':[.25,.7],'temperature':[.65,.95],'repetition_penalty':[1.1,1.3]}
                }},
                'selected_candidates':{'neutral_explain':'B'},'human_listening_qa':{'status':'accepted'}
            }
            (calibration/'05.json').write_text(json.dumps(profile), encoding='utf-8')
            content = {'article_id':'text1','primary_actor_id':'05','sentences':[{
                'id':'s01','discourse_function':'explain','prosody_focus':['crucial point'],
                'segments':[{'id':'s01-01','text':'The crucial point matters.','actor_id':'05','speaker_role':'narrator'}]
            }]}
            voice_profile = {'article_id':'text1','primary_actor_id':'05','article_arc':['setup','explain']}
            director = {'discourse_map':{'explain':{'director_intent':'neutral_explain','intensity':1}},'overrides':[]}
            plan = build_voice_plan(content, voice_profile, director, calibration)
            seg = plan['sentences'][0]['segments'][0]
            self.assertEqual(seg['director_intent'],'neutral_explain')
            self.assertEqual(seg['actor_id'],'05')
            self.assertEqual(seg['controls']['selected_variant'],'B')
            self.assertEqual(seg['controls']['artificial_pause_ms'],0)
            self.assertFalse(seg['controls']['post_tempo'])
            self.assertEqual(seg['prosody_focus'],['crucial point'])

    def test_unknown_discourse_hard_fails(self):
        with tempfile.TemporaryDirectory() as td:
            content={'article_id':'x','primary_actor_id':'05','sentences':[{'id':'s01','discourse_function':'mystery','segments':[]}]}
            with self.assertRaisesRegex(ValueError,'unmapped discourse'):
                build_voice_plan(content, {'article_id':'x','article_arc':['x']}, {'discourse_map':{},'overrides':[]}, Path(td))


if __name__ == '__main__':
    unittest.main()
