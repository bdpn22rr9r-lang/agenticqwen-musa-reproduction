"""禁止编造表述检查: 匹配"建议取/一般取/通常为/必须为/经验值/推荐 + 具体数值"等无依据表述。

计算类/抽取类豁免(它们有合法数值,见 rejection_and_boundary_rules.md §2)。
"""
from __future__ import annotations
import os, sys, argparse, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S

# 禁止模式: 模糊依据词 + 数值
FORBIDDEN = re.compile(
    r"(建议取|一般取|通常取|通常为|必须为|经验值[是为]?|推荐[取值是]?|宜取|可取)"
    r"[^，。；\n]{0,8}?"
    r"(\d+(?:\.\d+)?\s*(?:MPa|GPa|mm|µm|HRC|HBW|HV|%|°C|×10\^?\d+))",
    re.IGNORECASE,
)
EXEMPT = {"engineering_calculation", "context_extraction"}


def run(path: str) -> bool:
    recs = S.load_jsonl(path)
    problems = []
    for r in recs:
        if r.get("task_type") in EXEMPT:
            continue
        out = str(r.get("output", ""))
        hits = FORBIDDEN.findall(out)
        if hits:
            problems.append((r.get("id"), r.get("task_type"), hits))
    print(f"[forbidden] {path}: {len(recs)} 条, 含禁止表述 {len(problems)} 条")
    for rid, tt, hits in problems[:10]:
        print(f"  {rid} ({tt}): {hits}")
    return len(problems) == 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="禁止编造表述检查")
    ap.add_argument("inputs", nargs="+")
    a = ap.parse_args()
    ok = all(run(p) for p in a.inputs)
    sys.exit(0 if ok else 1)
