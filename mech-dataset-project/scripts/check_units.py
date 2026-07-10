"""单位格式检查: 数值与单位间应有空格、硬度标尺、常见混用。

简化规则(非全量 SI 校验,捕获常见书写问题):
  - "760MPa"(无数值单位空格) -> 建议改 "760 MPa"
  - "HRC45" / "Ra0.8"(标尺与数值粘连) -> 建议分开
  - 同一条同时出现 N/mm² 与 MPa(混用)
"""
from __future__ import annotations
import os, sys, argparse, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S

# 数值紧跟单位(无空格)的常见情形
NO_SPACE = re.compile(r"\d(?:MPa|GPa|kPa|Pa|mm|µm|HRC|HBW|HV|°C)\b")
# 硬度/粗糙度标尺前置粘连
SCALE_GLUE = re.compile(r"(?:HRC|HBW|HV|Ra|Rz)(\d)")


def run(path: str) -> bool:
    recs = S.load_jsonl(path)
    problems = []
    for r in recs:
        text = str(r.get("output", "")) + " " + str(r.get("input", ""))
        # 材料证据类保留原文格式,跳过
        if r.get("source_type") == "mechqa_converted":
            continue
        hits = NO_SPACE.findall(text)
        glue = SCALE_GLUE.findall(text)
        # 忽略括号内的单位等价说明(如 "MPa(N/mm²)")再判断是否混用
        text_no_paren = re.sub(r"（[^）]*）|\([^)]*\)", "", text)
        nm2 = ("N/mm²" in text_no_paren) or ("N/mm2" in text_no_paren)
        mpa = "MPa" in text_no_paren
        mix = nm2 and mpa
        if hits or glue or mix:
            problems.append((r.get("id"), {"no_space": hits[:5], "scale_glue": glue[:5], "mix_unit": mix}))
    print(f"[units] {path}: {len(recs)} 条, 格式问题 {len(problems)} 条")
    for rid, info in problems[:10]:
        print(f"  {rid}: {info}")
    return len(problems) == 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="单位格式检查")
    ap.add_argument("inputs", nargs="+")
    a = ap.parse_args()
    ok = all(run(p) for p in a.inputs)
    sys.exit(0 if ok else 1)
