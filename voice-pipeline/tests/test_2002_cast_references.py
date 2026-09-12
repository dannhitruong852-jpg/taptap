import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class CastReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=ROOT/'voice-pipeline/prepare_2002_cast_references.py';spec=importlib.util.spec_from_file_location('refs',path);cls.mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.mod)
    def test_materialized_actors_are_distinct_and_native_american_english(self):
        cfg=json.loads((ROOT/'voice-pipeline/config/cast_2002.json').read_text())
        self.mod.require_distinct_speakers(cfg['actors'])
        self.assertEqual(set(cfg['actors']),{'01','02','04','05','08','09','12','13'})
        self.assertTrue(all(a['native_language']=='american english' for a in cfg['actors'].values()))
    def test_member_resolution_never_falls_back_to_wrong_speaker_or_task(self):
        names=['p007/rainbow_01_regular.wav','p004/rainbow_01_regular.wav','p007/emo_interest_sentences.wav']
        self.assertEqual(self.mod.find_member(names,'p007','rainbow_01_regular'),'p007/rainbow_01_regular.wav')
        with self.assertRaises(ValueError):self.mod.find_member(names,'p008','rainbow_01_regular')
        with self.assertRaises(ValueError):self.mod.find_member(names,'p007','emo_amusement_sentences')
    def test_every_c_mode_emotion_has_a_reference_task(self):
        cfg=json.loads((ROOT/'voice-pipeline/config/cast_2002.json').read_text())
        self.assertEqual(set(cfg['reference_tasks']),{'neutral','warm','lively','serious','curious','ironic','tense','emotional'})
if __name__=='__main__':unittest.main()
