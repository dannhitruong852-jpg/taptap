import unittest

from generate_c_v4 import _load_article_profile, _build_plan


class Real2002VoicePlanIntegrationTests(unittest.TestCase):
    def test_profile_loader_reads_profiles_mapping(self):
        self.assertEqual(_load_article_profile(2002,'cloze')['primary_actor_id'],'04')
        self.assertEqual(_load_article_profile(2002,'text2')['primary_actor_id'],'08')
        self.assertEqual(_load_article_profile(2002,'translation')['primary_actor_id'],'02')

    def test_article_profile_not_legacy_content_actor_selects_narrator(self):
        expected={'cloze':'04','text1':'05','text2':'08','text3':'01','text4':'09','translation':'02'}
        for article,actor in expected.items():
            plan=_build_plan(2002,article)
            narrator=[seg for sentence in plan['sentences'] for seg in sentence['segments'] if seg.get('speaker_role')=='narrator']
            self.assertTrue(narrator,article)
            self.assertTrue(all(seg['actor_id']==actor for seg in narrator),(article,{seg['actor_id'] for seg in narrator}))

    def test_explicit_role_override_survives_article_cast(self):
        plan=_build_plan(2002,'text2')
        s10=next(s for s in plan['sentences'] if s['id']=='s10')
        self.assertEqual(s10['segments'][0]['actor_id'],'01')
        self.assertEqual(s10['segments'][0]['speaker_role'],'dave_lavery')
        self.assertEqual(s10['segments'][1]['actor_id'],'08')


if __name__=='__main__':
    unittest.main()
