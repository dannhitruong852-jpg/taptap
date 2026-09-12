import inspect
import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generate_c_v4 import deterministic_seed, select_sentence_shard, segment_fingerprint, build_candidate_entry
from merge_c_v4 import merge_status
from verify_c_v4 import verify_manifest


class C4RenderingTests(unittest.TestCase):
    def test_sentence_sharding_is_deterministic_and_complete(self):
        sentences=[{'id':f's{i:02d}'} for i in range(1,10)]
        shards=[select_sentence_shard(sentences,3,i) for i in range(3)]
        self.assertEqual(sorted(x['id'] for part in shards for x in part), sorted(x['id'] for x in sentences))
        self.assertEqual(shards[0], select_sentence_shard(sentences,3,0))
        self.assertEqual(len({x['id'] for part in shards for x in part}), len(sentences))

    def test_seed_and_fingerprint_are_stable_but_profile_sensitive(self):
        self.assertEqual(deterministic_seed(2002,'text1','s01','s01-01'), deterministic_seed(2002,'text1','s01','s01-01'))
        base={'actor_id':'05','director_intent':'neutral_explain','intensity':1,'profile_hash':'aaa','calibration_id':'c1','exaggeration':.5,'cfg_weight':.4,'temperature':.8,'repetition_penalty':1.18,'reference_path':'actor05-neutral.wav'}
        a=segment_fingerprint('Hello world.', base, 'refsha', 123)
        b=segment_fingerprint('Hello world.', {**base,'profile_hash':'bbb'}, 'refsha', 123)
        self.assertNotEqual(a,b)

    def test_candidate_entry_keeps_human_qa_pending_and_zero_pause(self):
        controls={'actor_id':'05','director_intent':'neutral_explain','intensity':1,'profile_hash':'abc','calibration_id':'c1','selected_variant':'B','reference_path':'actor05-neutral.wav','reference_state':'neutral','exaggeration':.5,'cfg_weight':.4,'temperature':.8,'repetition_penalty':1.18,'artificial_pause_ms':0,'post_tempo':False,'approval_status':'accepted'}
        entry=build_candidate_entry('s01-01','Hello.',controls,'refsha',123,1.2,{'x.opus':'a','x.mp3':'b'})
        self.assertEqual(entry['artificial_pause_ms'],0)
        self.assertFalse(entry['post_tempo'])
        self.assertEqual(entry['qa'],{'technical':'passed','voice':'pending','c_direction':'pending'})

    def test_v4_sources_prohibit_global_performance_and_tempo_padding(self):
        import generate_c_v4, merge_c_v4
        src=inspect.getsource(generate_c_v4)+inspect.getsource(merge_c_v4)
        self.assertNotIn('PERFORMANCE=', src.replace(' ',''))
        self.assertNotIn('atempo=', src)
        self.assertNotIn('apad', src)

    def test_merge_status_requires_all_six_units(self):
        articles=['cloze','text1','text2','text3','text4','translation']
        complete={a:{'missing':[],'sentences':1} for a in articles}
        self.assertEqual(merge_status(complete),'complete_candidate')
        complete['text2']['missing']=['s01-01']
        self.assertEqual(merge_status(complete),'partial_candidate')

    def test_manifest_verifier_never_promotes_human_qa(self):
        manifest={'article':'text1','c_mode_version':'v4','sentences':{'s01':{
            'duration_seconds':1.0,'actor_sequence':['05'],'files':{'v4-s01.opus':'abc','v4-s01.mp3':'def'},
            'qa':{'technical':'passed','voice':'pending','c_direction':'pending'},
            'artificial_pause_ms':0,'post_tempo':False,'generation_fingerprint':'g'
        }}}
        errors=verify_manifest(manifest, require_files=False)
        self.assertEqual(errors,[])
        manifest['sentences']['s01']['qa']['voice']='passed'
        self.assertTrue(any('human QA' in e for e in verify_manifest(manifest, require_files=False)))


if __name__=='__main__':
    unittest.main()
