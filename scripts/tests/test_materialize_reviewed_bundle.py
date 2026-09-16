import io,json,tarfile,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from materialize_reviewed_bundle import materialize

class T(unittest.TestCase):
    def _write_bundle(self,bundle,rows,qa_extra=None):
        with tarfile.open(bundle,'w:gz') as tf:
            for year in (2011,2012):
                d=tarfile.TarInfo(str(year)); d.type=tarfile.DIRTYPE; tf.addfile(d)
                for unit in ('cloze','text1','text2','text3','text4','partb','translation'):
                    qa={'source_scope_verified':True,'translation_alignment_reviewed':True}
                    if qa_extra: qa.update(qa_extra)
                    doc={'year':year,'article':{'id':unit,'rows':rows},'qa':qa}
                    data=(json.dumps(doc,ensure_ascii=False)+'\n').encode(); info=tarfile.TarInfo(f'{year}/{unit}.candidate.json'); info.size=len(data); tf.addfile(info,io.BytesIO(data))

    def test_materializes_exact_reviewed_set_with_directory_entries(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); bundle=td/'x.tgz'; root=td/'out'
            self._write_bundle(bundle,[[1,'English','中文','explain',[]]])
            written=materialize(bundle,root); self.assertEqual(len(written),14); self.assertTrue((root/'2012/text4.candidate.json').is_file())

    def test_materializes_one_reviewed_row_as_sentence_rows_without_changing_text(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); bundle=td/'x.tgz'; root=td/'out'
            self._write_bundle(
                bundle,
                [[1,'Alpha.|Beta?','甲。乙？','explain',[]]],
                {'sentence_count':2},
            )
            materialize(bundle,root)
            doc=json.loads((root/'2011/text1.candidate.json').read_text(encoding='utf-8'))
            self.assertEqual(
                doc['article']['rows'],
                [[1,'Alpha.','甲。','explain',[]],[2,'Beta?','乙？','explain',[]]],
            )
            self.assertEqual(''.join(r[1] for r in doc['article']['rows']),'Alpha.Beta?')
            self.assertEqual(''.join(r[2] for r in doc['article']['rows']),'甲。乙？')

    def test_rejects_unaligned_chinese_sentence_boundaries(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); bundle=td/'x.tgz'; root=td/'out'
            self._write_bundle(
                bundle,
                [[1,'Alpha.|Beta?','甲乙。','explain',[]]],
                {'sentence_count':2},
            )
            with self.assertRaises(ValueError):
                materialize(bundle,root)

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); bundle=td/'x.tgz'
            with tarfile.open(bundle,'w:gz') as tf:
                data=b'{}'; info=tarfile.TarInfo('../evil.json'); info.size=len(data); tf.addfile(info,io.BytesIO(data))
            with self.assertRaises(ValueError): materialize(bundle,td/'out')
if __name__=='__main__': unittest.main()
