"""主格式 -> LLaMA-Factory alpaca 格式 + dataset_info.json。

把 *_master.jsonl 投影成 {instruction,input,output} 的 alpaca json,
并生成/合并 dataset_info.json(columns 映射 prompt=instruction/query=input/response=output)。
"""
from __future__ import annotations
import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S


def export_alpaca(master_jsonl: str, out_alpaca: str) -> int:
    recs = S.load_jsonl(master_jsonl)
    alpaca = [S.dict_to_record(r).to_alpaca() for r in recs]
    S.save_json(alpaca, out_alpaca)
    return len(alpaca)


def write_dataset_info(release_dir: str, dataset_name: str, train_file: str) -> str:
    info_path = os.path.join(release_dir, "dataset_info.json")
    info = S.load_json(info_path) if os.path.exists(info_path) else {}
    info[dataset_name] = {
        "file_name": train_file,
        "columns": {"prompt": "instruction", "query": "input", "response": "output"},
    }
    S.save_json(info, info_path)
    return info_path


def main():
    ap = argparse.ArgumentParser(description="导出 alpaca + dataset_info")
    ap.add_argument("-r", "--release-dir", default="data/releases/v0.1-seed")
    ap.add_argument("-n", "--name", default="mech_sft_v0_1_seed")
    a = ap.parse_args()
    rd = a.release_dir
    tr = export_alpaca(os.path.join(rd, "train_master.jsonl"), os.path.join(rd, "train_alpaca.json"))
    va = export_alpaca(os.path.join(rd, "validation_master.jsonl"), os.path.join(rd, "validation_alpaca.json"))
    # test/challenge 也投影(供评测用)
    te = export_alpaca(os.path.join(rd, "test_master.jsonl"), os.path.join(rd, "test_alpaca.json")) if os.path.exists(os.path.join(rd, "test_master.jsonl")) else 0
    ch = export_alpaca(os.path.join(rd, "challenge_master.jsonl"), os.path.join(rd, "challenge_alpaca.json")) if os.path.exists(os.path.join(rd, "challenge_master.jsonl")) else 0
    info = write_dataset_info(rd, a.name, "train_alpaca.json")
    print(f"[export] train={tr} validation={va} test={te} challenge={ch} -> {rd}")
    print(f"[export] dataset_info -> {info}  (dataset_name={a.name})")


if __name__ == "__main__":
    main()
