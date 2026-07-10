"""注册数据集到 LlamaFactory(复用 mechqa-qwen-lora v1/v2 的注册逻辑)。

本机无 LlamaFactory。默认只打印远程注册命令;若提供 --lf-data 目录,
则把 alpaca json 复制过去并合并 dataset_info(模拟 v1/v2 build 脚本的注册步)。

参考: mech-qwen-sft-v1/scripts/build_mech_dataset_v1.py 第 173-179 行的注册逻辑。
"""
from __future__ import annotations
import os, sys, argparse, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S


def main():
    ap = argparse.ArgumentParser(description="注册到 LlamaFactory")
    ap.add_argument("-r", "--release-dir", default="data/releases/v0.1-seed")
    ap.add_argument("-n", "--name", default="mech_sft_v0_1_seed")
    ap.add_argument("--lf-data", default="", help="LlamaFactory 的 data/ 目录;提供则复制并注册")
    a = ap.parse_args()
    rd = a.release_dir
    train = os.path.join(rd, "train_alpaca.json")
    info_path = os.path.join(rd, "dataset_info.json")

    print("[register] 远程注册命令(在 mech-qwen-sft-official 容器内执行):")
    print("  LF=/workspace/mech-qwen-sft/third_party/LlamaFactory_MUSA")
    print(f"  cp <本仓库>/mech-dataset-project/{rd}/train_alpaca.json $LF/data/{a.name}.json")
    print(f"  # 把 {rd}/dataset_info.json 中 \"{a.name}\" 条目合并进 $LF/data/dataset_info.json")
    print("  # columns: prompt=instruction, query=input, response=output")
    print("  MUSA_LAUNCH_BLOCKING=1 MUSA_VISIBLE_DEVICES=0 \\")
    print(f"    llamafactory-cli train <config>.yaml   # dataset: {a.name}")

    if a.lf_data:
        os.makedirs(a.lf_data, exist_ok=True)
        if os.path.exists(train):
            shutil.copy2(train, os.path.join(a.lf_data, f"{a.name}.json"))
        lf_info_path = os.path.join(a.lf_data, "dataset_info.json")
        info = S.load_json(lf_info_path) if os.path.exists(lf_info_path) else {}
        rel_info = S.load_json(info_path) if os.path.exists(info_path) else {}
        info.update(rel_info)
        S.save_json(info, lf_info_path)
        print(f"[register] 已复制到 {a.lf_data} 并合并 dataset_info")


if __name__ == "__main__":
    main()
