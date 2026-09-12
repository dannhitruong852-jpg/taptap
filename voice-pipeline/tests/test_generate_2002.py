import tempfile
import unittest
from pathlib import Path
from generate_2002 import run_segments, render_fingerprint, cache_valid, spoken_text
SEGMENT={'id':'s01-01','text':'Hello there.','actor_id':'05','rate':1.0,'exaggeration':.55,'cfg_weight':.45,'pause_after_ms':80,'pause_before_ms':0,'emotion':'warm','intensity':1,'speaker_role':'narrator'}

class Generate2002Tests(unittest.TestCase):
    def test_every_sound_input_invalidates_cache(self):
        initial=render_fingerprint(SEGMENT,'ref1',2002)
        for key,value in [('text','Different.'),('rate',1.02),('exaggeration',.6),('cfg_weight',.4),('pause_after_ms',120)]:
            self.assertNotEqual(initial,render_fingerprint({**SEGMENT,key:value},'ref1',2002),key)
        self.assertNotEqual(initial,render_fingerprint(SEGMENT,'ref2',2002))
        self.assertNotEqual(initial,render_fingerprint(SEGMENT,'ref1',2003))
    def test_fail_soft_retry_and_manifest_cache_are_real(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);calls=[]
            bad={**SEGMENT,'id':'s02-01'}
            def render(segment,seed,output):
                calls.append((segment['id'],seed))
                if segment['id']=='s02-01': raise RuntimeError('isolated failure')
                (output/f"{segment['id']}.opus").write_bytes(b'encoded opus')
                (output/f"{segment['id']}.mp3").write_bytes(b'encoded mp3')
                return {'duration_seconds':2.0,'qa_status':'candidate','technical_qa':'passed'}
            report=run_segments([SEGMENT,bad],root,render,{'05':'ref1'},'text1',max_attempts=2)
            self.assertEqual(len(report['segments']),1)
            self.assertEqual(len(report['failures']),1)
            self.assertEqual(sum(c[0]=='s02-01' for c in calls),2)
            before=len(calls)
            again=run_segments([SEGMENT],root,render,{'05':'ref1'},'text1',max_attempts=2)
            self.assertEqual(len(calls),before)
            self.assertEqual(again['cache_hits'],1)
            (root/'s01-01.opus').write_bytes(b'tampered')
            self.assertFalse(cache_valid(again['segments']['s01-01'],root))
    def test_spoken_normalization_does_not_change_source(self):
        text='$22 and 0.25-0.5% of GDP.'
        said=spoken_text(text)
        self.assertEqual(text,'$22 and 0.25-0.5% of GDP.')
        self.assertIn('twenty-two dollars',said)
        self.assertIn('zero point two five to zero point five percent',said)
        self.assertIn('G D P',said)
