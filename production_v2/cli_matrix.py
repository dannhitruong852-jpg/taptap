import argparse
import json
from pathlib import Path

from .matrix import build_render_matrix


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--catalog', required=True)
    parser.add_argument('--shards', type=int, default=3)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)

    manifest = json.loads(Path(args.manifest).read_text())
    catalog = json.loads(Path(args.catalog).read_text())
    matrix = build_render_matrix(manifest, catalog, args.shards)
    Path(args.output).write_text(json.dumps(matrix, separators=(',', ':')) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
