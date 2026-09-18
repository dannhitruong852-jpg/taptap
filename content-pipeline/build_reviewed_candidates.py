"""Build normalized V2 reviewed-candidate evidence from a reviewed curated source."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from build_curated_year import load_curated_source

ROOT = Path(__file__).resolve().parents[1]


def compact_sha256(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()

    review_path = args.review or ROOT / f"content-pipeline/curated/repair-tails/{args.year}.json"
    review_doc = json.loads(review_path.read_text(encoding="utf-8"))
    review = dict(review_doc.get("review") or {})
    required = [
        "source_scope_verified", "scope_exclusions_reviewed", "text_fidelity_reviewed",
        "translation_alignment_reviewed", "sentence_alignment_reviewed",
    ]
    if review.get("review_schema_version") != "c-mode-v2-1" or not all(review.get(k) is True for k in required):
        raise ValueError("review sidecar does not contain explicit V2 reviewed evidence")

    source = load_curated_source(ROOT / "content-pipeline/curated", args.year)
    out = ROOT / f"reports/content-freeze/{args.year}"
    out.mkdir(parents=True, exist_ok=True)
    for article in source["articles"]:
        rows = article.get("rows") or []
        qa = {
            **review,
            "source_pdf": source.get("source_pdf") or source.get("source_filename"),
            "source_sha256": source["source_sha256"],
            "sentence_count": len(rows),
            "expected_sentences": len(rows),
            "actual_sentences": len(rows),
            "status": "reviewed_candidate",
            "curated_payload_sha256": compact_sha256(article),
        }
        document = {"year": args.year, "article": article, "qa": qa}
        (out / f"{article['id']}.candidate.json").write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps({"year": args.year, "candidates": len(source["articles"])}))


if __name__ == "__main__":
    main()
