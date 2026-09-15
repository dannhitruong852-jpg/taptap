import io,json,tarfile,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from materialize_reviewed_bundle import materialize

class T(unittest.TestCase):
    def test_materializes_exact_reviewed_set_with_directory_entries(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); bundle=td/'x.tgz'; root=td/'out'
            with tarfile.open(bundle,'w:gz') as tf:
                for year in (2011,2012):
                    d=tarfile.TarInfo(str(year)); d.type=tarfile.DIRTYPE; tf.addfile(d)
                    for unit in ('cloze','text1','text2','text3','text4','partb','translation'):
                        doc={'year':year,'article':{'id':unit,'rows':[[1,'English','中文','explain',[]]]},'qa':{'source_scope_verified':True,'translation_alignment_reviewed':True}}
                        data=(json.dumps(doc,ensure_ascii=False)+'\n').encode(); info=tarfile.TarInfo(f'{year}/{unit}.candidate.json'); info.size=len(data); tf.addfile(info,io.BytesIO(data))
            written=materialize(bundle,root); self.assertEqual(len(written),14); self.assertTrue((root/'2012/text4.candidate.json').is_file())
    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); bundle=td/'x.tgz'
            with tarfile.open(bundle,'w:gz') as tf:
                data=b'{}'; info=tarfile.TarInfo('../evil.json'); info.size=len(data); tf.addfile(info,io.BytesIO(data))
            with self.assertRaises(ValueError): materialize(bundle,td/'out')
if __name__=='__main__': unittest.main()
