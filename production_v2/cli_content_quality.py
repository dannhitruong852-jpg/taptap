import argparse
import json
from pathlib import Path

from .content_quality import validate_content_quality


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--catalog',required=True)
    parser.add_argument('--root',required=True)
    parser.add_argument('--report',required=True)
    args=parser.parse_args(argv)
    manifest=json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    catalog=json.loads(Path(args.catalog).read_text(encoding='utf-8'))
    report=validate_content_quality(manifest,catalog,Path(args.root))
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0 if report['ok'] else 2


if __name__=='__main__':
    raise SystemExit(main())
