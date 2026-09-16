import argparse
import json
from pathlib import Path

from .manifest import build_manifest, validate_manifest
from .pipeline_state import can_transition


def _read(path):
    return json.loads(Path(path).read_text())


def _write(path, doc):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + '.tmp')
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(target)


def _parser():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)

    create = sub.add_parser('create')
    create.add_argument('--batch-id', required=True)
    create.add_argument('--years', required=True)
    create.add_argument('--source-ref', required=True)
    create.add_argument('--output', required=True)

    validate = sub.add_parser('validate')
    validate.add_argument('--manifest', required=True)

    advance = sub.add_parser('advance')
    advance.add_argument('--manifest', required=True)
    advance.add_argument('--to', required=True)
    advance.add_argument('--output', required=True)

    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.command == 'create':
        years = [int(value) for value in args.years.split(',') if value.strip()]
        doc = build_manifest(args.batch_id, years, args.source_ref)
        errors = validate_manifest(doc)
        if errors:
            raise SystemExit('; '.join(errors))
        _write(args.output, doc)
        return 0

    if args.command == 'validate':
        errors = validate_manifest(_read(args.manifest))
        if errors:
            raise SystemExit('; '.join(errors))
        return 0

    doc = _read(args.manifest)
    errors = validate_manifest(doc)
    if errors:
        raise SystemExit('; '.join(errors))
    if not can_transition(doc['state'], args.to):
        raise SystemExit(f'illegal state transition: {doc["state"]} -> {args.to}')
    doc['state'] = args.to
    _write(args.output, doc)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
