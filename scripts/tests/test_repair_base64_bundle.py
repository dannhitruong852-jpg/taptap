import base64,gzip,sys,unittest
sys.path.insert(0,'scripts')
from repair_base64_bundle import repair_chunks
class T(unittest.TestCase):
 def test_repairs_one_missing_base64_character(self):
  raw=b'hello reviewed bundle'*100
  enc=base64.b64encode(gzip.compress(raw)).decode()
  chunks=[enc[i:i+8] for i in range(0,len(enc),8)]
  victim=2
  chunks[victim]=chunks[victim][:3]+chunks[victim][4:]
  self.assertEqual(gzip.decompress(repair_chunks(chunks)),raw)
if __name__=='__main__': unittest.main()
