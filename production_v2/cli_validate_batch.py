import argparse
import json
from pathlib import Path

from .content_quality import validate_content_quality
from .validate_batch import validate_batch


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--catalog',required=True)
    parser.add_argument('--reader-root',required=True)
    parser.add_argument('--phase',choices=['preflight','freeze','release'],default='preflight')
    parser.add_argument('--report',required=True)
    args=parser.parse_args(argv)

    manifest=json.loads(Path(args.manifest).read_text())
    catalog=json.loads(Path(args.catalog).read_text())
    reader_root=Path(args.reader_root)
    report=validate_batch(manifest,catalog,reader_root,args.phase)

    if args.phase in {'preflight','freeze'}:
        quality=validate_content_quality(manifest,catalog,reader_root.parent)
        report['content_quality']=quality
        report['errors']=[*report.get('errors',[]),*quality.get('errors',[])]
        report['ok']=bool(report.get('ok')) and bool(quality.get('ok'))

    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return 0 if report['ok'] else 2


if __name__=='__main__':
    raise SystemExit(main())
