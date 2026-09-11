import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ConfigTest(unittest.TestCase):
    def test_actor_and_emotion_registry(self):
        actors = json.loads((ROOT / 'config/actors.json').read_text())['actors']
        emotions = json.loads((ROOT / 'config/emotions.json').read_text())['emotions']
        self.assertEqual([a['id'] for a in actors], [f'{i:02d}' for i in range(1,16)])
        self.assertEqual(sum(a['accent']=='en-US' for a in actors), 13)
        self.assertEqual(sum(a['accent']=='en-GB' for a in actors), 2)
        self.assertEqual(set(emotions), {'neutral','warm','lively','serious','curious','ironic','tense','emotional'})
        self.assertEqual(actors[4]['id'],'05')
        self.assertEqual(actors[11]['id'],'12')
        self.assertEqual(actors[12]['id'],'13')

if __name__ == '__main__':
    unittest.main()
