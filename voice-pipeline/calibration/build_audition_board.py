"""Build a portable static comparison board from actor audition manifests."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


def build_board(manifest_dir: Path, output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    manifests = []
    for path in sorted(manifest_dir.rglob("*.json")):
        candidate = json.loads(path.read_text())
        if "actor_id" in candidate and "renders" in candidate:
            manifests.append(candidate)
    payload = {"schema_version": "c-v4-audition-board-1", "human_voice_qa": "pending", "actors": manifests}
    (output / "auditions.json").write_text(json.dumps(payload, indent=2) + "\n")
    sections = []
    for manifest in manifests:
        actor = html.escape(manifest["actor_id"])
        groups = {}
        for render in manifest.get("renders", []):
            groups.setdefault(render["scene_id"], []).append(render)
        cards = []
        for scene_id, renders in groups.items():
            choices = "".join(
                f'<label><strong>{html.escape(r["variant"])} · {html.escape(r["delivery"])}</strong>'
                f'<audio controls preload="none" src="../audio/actor{actor}/{html.escape(r["audio"]["opus"]["path"])}"></audio>'
                f'<code>exaggeration={r["exaggeration"]} cfg={r["cfg_weight"]} seed={r["seed"]}</code></label>'
                for r in renders
            )
            cards.append(f'<article><h3>{html.escape(scene_id)} · {html.escape(renders[0]["category"])}</h3><p>{html.escape(renders[0]["text"])}</p><div class="choices">{choices}</div></article>')
        benchmark = '<p class="benchmark">Actor 05 / Text 1 human-naturalness benchmark — quality reference only, not a default voice.</p>' if actor == "05" else ""
        sections.append(f'<section><h2>Actor {actor}</h2>{benchmark}<p class="pending">Voice QA: pending · eligible: false</p>{"".join(cards)}</section>')
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>C v4 actor auditions</title><style>
body{font:16px system-ui;max-width:1200px;margin:auto;padding:24px;background:#f5f3ee;color:#25231f}section,article{background:white;border:1px solid #d8d2c5;border-radius:12px;padding:16px;margin:16px 0}.choices{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}label,audio,code{display:block;width:100%;margin-top:8px}.pending{color:#9b3d28;font-weight:700}.benchmark{border-left:4px solid #5b6f95;padding-left:10px}@media(max-width:760px){.choices{grid-template-columns:1fr}}</style>
<body><h1>C v4 Actor Calibration Auditions</h1><p>Compare naturalness, continuity, semantic emphasis, and actor identity. CI performs technical checks only; this board never approves Voice QA.</p>""" + "".join(sections) + "</body></html>"
    index = output / "index.html"
    index.write_text(page)
    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_board(args.manifests, args.output)
