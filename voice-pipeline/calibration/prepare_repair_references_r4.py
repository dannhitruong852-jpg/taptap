"""Prepare extra same-speaker references for C v4 repair round four."""
from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path

from calibration.prepare_expansion_references import (
    EARS_RELEASE,
    SOURCES,
    _find_ears_member,
    _write_reference,
    fetch,
    prepare,
    sha256_bytes,
    sha256_file,
)

EXTRA_REFERENCE_TASKS = {
    "03": {
        "r4_lowpitch1": "rainbow_01_lowpitch",
        "r4_lowpitch2": "rainbow_02_lowpitch",
    },
    "14": {
        "r4_fast1": "rainbow_01_fast",
        "r4_fast2": "rainbow_02_fast",
    },
}


def prepare_round4(actor_id: str, output: Path) -> dict:
    if actor_id not in EXTRA_REFERENCE_TASKS:
        raise ValueError(f"actor {actor_id} has no round-four extra references")
    report = prepare(actor_id, output)
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["actors"]
    cfg = sources[actor_id]
    if cfg["source_corpus"] != "EARS":
        raise ValueError("round-four extra reference strategy currently requires EARS")
    speaker = cfg["source_speaker"]
    with tempfile.TemporaryDirectory() as td_raw:
        archive = Path(td_raw) / f"{speaker}.zip"
        fetch(EARS_RELEASE + f"{speaker}.zip", archive)
        if sha256_file(archive) != report["archive_sha256"]:
            raise ValueError("EARS archive changed between base and round-four preparation")
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            extras = {}
            for state, task in EXTRA_REFERENCE_TASKS[actor_id].items():
                member = _find_ears_member(names, speaker, task)
                raw = z.read(member)
                target = output / f"actor{actor_id}-{state}.wav"
                metrics = _write_reference(raw, target)
                extras[state] = {
                    "path": target.name,
                    "task": task,
                    "source_member": member,
                    "source_sha256": sha256_bytes(raw),
                    **metrics,
                }
    report["round4_extra_variants"] = extras
    (output / f"actor{actor_id}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare_round4(args.actor, args.output)
