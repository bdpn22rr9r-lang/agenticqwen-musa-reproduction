#!/usr/bin/env python3
"""Convert HotpotQA HF parquet shards -> original hotpot_train_v1.1.json format (DERIVED).

Input : one or more *distractor train* parquet shards from
        https://huggingface.co/datasets/hotpotqa/hotpot_qa
        (e.g. distractor/train-00000-of-00002.parquet, train-00001-of-00002.parquet)
Output: a single JSON array matching the original CMU hotpot_train_v1.1.json schema
        (_id, question, answer, supporting_facts[[title,sent_id]],
         context[[title,sentences]], type, level).

NOTE - this is a DERIVED file:
  * HF stores supporting_facts / context as structs {title:[...], sent_id/sentences:[...]}.
    This script restores the original list-of-lists shape.
  * Content is equivalent to the CMU train file (90,447 rows verified), but the
    bytes are NOT identical (field order / spacing / unicode escaping differ), so
    the SHA256 differs from the official CMU hash 26650cf5....  Treat the output
    as derived, not as a byte-identical copy of the CMU original.

Usage:
  python hotpotqa_parquet_to_json.py shard1.parquet shard2.parquet \
      -o hotpot_train_v1.1.derived.json
"""
import argparse
import json

import pyarrow.parquet as pq


def to_original(row: dict) -> dict:
    sf = row["supporting_facts"]
    supporting = [[t, i] for t, i in zip(sf["title"], sf["sent_id"])]
    ctx = row["context"]
    context = [[t, s] for t, s in zip(ctx["title"], ctx["sentences"])]
    return {
        "_id": row["id"],
        "question": row["question"],
        "answer": row["answer"],
        "supporting_facts": supporting,
        "context": context,
        "type": row["type"],
        "level": row["level"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("shards", nargs="+", help="parquet shard paths (in order)")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    out = []
    for shard in args.shards:
        out.extend(to_original(r) for r in pq.read_table(shard).to_pylist())

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)

    print(f"records={len(out)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
