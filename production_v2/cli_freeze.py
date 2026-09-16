import argparse
import json
from pathlib import Path

from .freeze import build_freeze_report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--catalog', required=True)
    parser.add_argument('--reader-root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)

    manifest = json.loads(Path(args.manifest).read_text())
    catalog = json.loads(Path(args.catalog).read_text())
    report = build_freeze_report(manifest, catalog, Path(args.reader_root))
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
