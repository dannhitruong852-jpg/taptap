"""Recover a reviewed curated year whose legacy gzip/base64 shards were truncated.

The original shards are never rewritten. A small reviewed repair sidecar identifies the
exact truncation point and supplies only the missing rows/articles. The recovered full
JSON is written as curated/<year>.json, which the canonical compiler already prefers.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--repair", type=Path)
    args = parser.parse_args()

    curated = ROOT / "content-pipeline/curated"
    repair_path = args.repair or curated / "repair-tails" / f"{args.year}.json"
    spec = json.loads(repair_path.read_text(encoding="utf-8"))
    if int(spec["year"]) != args.year:
        raise ValueError("repair year disagrees with --year")

    parts = sorted(curated.glob(f"{args.year}.json.gz.b64.part*"))
    if not parts:
        raise FileNotFoundError(f"no legacy shards for {args.year}")
    encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    encoded += "=" * (-len(encoded) % 4)
    dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
    recovered = dec.decompress(base64.b64decode(encoded)).decode("utf-8")
    if dec.eof:
        raise ValueError("legacy stream is already complete; repair sidecar must not be applied")

    marker = spec["truncate_marker"]
    cut = recovered.find(marker)
    if cut < 0:
        raise ValueError("repair truncate marker not found")
    prefix = recovered[:cut]
    digest = hashlib.sha256(prefix.encode("utf-8")).hexdigest()
    if digest != spec["expected_prefix_sha256"]:
        raise ValueError(f"reviewed prefix hash mismatch: {digest}")

    suffix = "".join(
        "," + json.dumps(row, ensure_ascii=False, separators=(",", ":"))
        for row in spec["partb_rows_tail"]
    )
    suffix += "]}"
    for article in spec.get("remaining_articles", []):
        suffix += "," + json.dumps(article, ensure_ascii=False, separators=(",", ":"))
    suffix += "]}"

    text = prefix + suffix
    document = json.loads(text)
    if int(document.get("year", -1)) != args.year:
        raise ValueError("recovered document year mismatch")
    expected = ["cloze", "text1", "text2", "text3", "text4", "partb", "translation"]
    actual = [article.get("id") for article in document.get("articles", [])]
    if actual != expected:
        raise ValueError(f"recovered article inventory mismatch: {actual}")

    target = curated / f"{args.year}.json"
    target.write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"year": args.year, "articles": len(actual), "target": str(target)}))


if __name__ == "__main__":
    main()
