import json
import tempfile
import unittest
from pathlib import Path
from merge_2002 import merge_article
from generate_2002 import sha, render_fingerprint
SEG={'id':'s01-01','text':'Test.','actor_id':'05','rate':1,'exaggeration':.5,'cfg_weight':.5}
DOC={'article_id':'text1','sentences':[{'segments':[SEG, {**SEG,'id':'s02-01'}]}]}
class MergeTests(unittest.TestCase):
    def test_only_matching_and_intact_audio_is_published(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'incoming';source.mkdir();out=root/'out';files={}
            for ext in ['opus','mp3']:
                path=source/f's01-01.{ext}';path.write_bytes(b'audio');files[path.name]=sha(path)
            entry={'path':'./audio/2002/c-text1/s01-01.opus','mp3_path':'./audio/2002/c-text1/s01-01.mp3','files':files,'seed':3,'reference_sha256':'ref','fingerprint':render_fingerprint(SEG,'ref',3),'qa_status':'candidate'}
            manifest=source/'shard-0.json';manifest.write_text(json.dumps({'article':'text1','segments':{'s01-01':entry}}))
            result=merge_article(DOC,[manifest],out)
            self.assertEqual(len(result['segments']),1)
            self.assertEqual(result['missing'],['s02-01'])
            self.assertTrue((out/'s01-01.opus').exists())
            (source/'s01-01.opus').write_bytes(b'bad')
            self.assertEqual(merge_article(DOC,[manifest],root/'reject')['segments'],{})
