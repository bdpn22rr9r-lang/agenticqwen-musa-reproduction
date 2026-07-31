#!/usr/bin/env python3
"""Convert Omni-Math.jsonl -> instruction-tuning format (DERIVED, schema PROVISIONAL).

Omni-Math.jsonl fields : domain, difficulty, problem, solution, answer, source
Output (one JSON per line): {"instruction", "output", "answer", "meta": {...}}

NOTE - PROVISIONAL conversion:
  The exact AgenticQwen training schema is NOT yet defined in this project
  (training/ is empty; the task book specifies no concrete schema). This script
  emits a generic instruction-tuning shape. Once the AgenticQwen schema is fixed
  (e.g. {"messages":[...]} / {"conversations":[...]}), adjust the output mapping.
  Treat the output as DERIVED, not final training data.

Usage:
  python omni_math_to_instruction.py Omni-Math.jsonl -o omni-math.instruction.jsonl
"""
import argparse
import json


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="Omni-Math.jsonl")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    n = 0
    with open(args.input, encoding="utf-8") as fi, open(args.output, "w", encoding="utf-8") as fo:
        for line in fi:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            out = {
                "instruction": r.get("problem", ""),
                "output": r.get("solution", ""),
                "answer": r.get("answer", ""),
                "meta": {
                    "domain": r.get("domain"),
                    "difficulty": r.get("difficulty"),
                    "source": r.get("source"),
                },
            }
            fo.write(json.dumps(out, ensure_ascii=False) + "\n")
            n += 1
    print(f"records={n} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
