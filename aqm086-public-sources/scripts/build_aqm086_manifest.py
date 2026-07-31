#!/usr/bin/env python3
"""Idempotently update the computable fields of the AQM086 master manifest.

Reads every manifests/*.manifest.json (except the master), recomputes the
training-eligible reasoning/agentic counts, and updates the master manifest
IN PLACE - preserving all human-maintained fields (release, acceptance,
existing_public_data, eligible_breakdown, notes, ...).

A source counts as eligible only when ALL of:
  license_status == "CONFIRMED" AND training_eligible == true
  AND download_status == "OK" AND record_count is a positive int.

Run after adding/editing a source manifest:
  python build_aqm086_manifest.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST_DIR = HERE.parent / "manifests"
MASTER = MANIFEST_DIR / "AQM086-public-sources.manifest.json"

EXISTING = 37022  # bastion public-effective-37022.jsonl
TARGET = 100000


def eligible(s: dict) -> bool:
    return (s.get("license_status") == "CONFIRMED"
            and s.get("training_eligible") is True
            and s.get("download_status") == "OK"
            and isinstance(s.get("record_count"), int)
            and s["record_count"] > 0)


def main() -> int:
    if not MASTER.exists():
        print(f"ERROR: master manifest not found: {MASTER}", file=sys.stderr)
        return 2
    master = json.loads(MASTER.read_text(encoding="utf-8"))
    source_files, reasoning, agentic = [], 0, 0
    for jf in sorted(MANIFEST_DIR.glob("*.manifest.json")):
        if jf == MASTER:
            continue
        s = json.loads(jf.read_text(encoding="utf-8"))
        source_files.append(f"manifests/{jf.name}")
        if eligible(s):
            n = int(s["record_count"])
            if str(s.get("source_type", "")).startswith("reasoning"):
                reasoning += n
            elif str(s.get("source_type", "")).startswith("agentic"):
                agentic += n

    total = EXISTING + reasoning + agentic
    master["source_manifests"] = source_files
    master["reasoning_public_examples"] = reasoning
    master["agentic_public_examples"] = agentic
    master["total_training_eligible_so_far"] = total
    master["remaining_to_target"] = max(TARGET - total, 0)

    MASTER.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "sources": len(source_files),
        "reasoning_eligible": reasoning,
        "agentic_eligible": agentic,
        "existing": EXISTING,
        "total_eligible": total,
        "remaining_to_target": master["remaining_to_target"],
    }, ensure_ascii=False, indent=2))
    print(f"updated {MASTER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
