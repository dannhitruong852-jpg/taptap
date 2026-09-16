import argparse
import json
from pathlib import Path

from .release_guard import compare_catalogs


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--old', required=True)
    parser.add_argument('--new', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args(argv)

    old = json.loads(Path(args.old).read_text())
    new = json.loads(Path(args.new).read_text())
    report = compare_catalogs(old, new)
    Path(args.report).write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['ok'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
