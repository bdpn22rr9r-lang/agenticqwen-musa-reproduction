# MUSA GPU 短时训练证明包

## 目标

在 60～120 秒内完成以下证明：

1. 服务器能识别摩尔线程 GPU；
2. Torch-MUSA 可以在 GPU 上执行；
3. 每张可见 GPU 都进行了前向传播、反向传播和 AdamW 参数更新；
4. 训练前后模型参数摘要发生变化；
5. GPU 使用过程由 `mthreads-gmi` 周期性记录；
6. 生成可归档的日志、JSON、CSV 和 SHA256 校验文件。

本方案默认让每张 GPU 独立训练同一个小型神经网络副本。这样不依赖 MCCL，
适合作为第一份稳定的 GPU 使用证明。它证明了所有卡都实际执行了训练计算，
但不等价于“单个模型进行了 8 卡分布式数据并行训练”。

## 运行

```bash
cd musa_gpu_proof
chmod +x run_gpu_proof.sh
bash run_gpu_proof.sh
```

默认使用 GPU 0～7，运行 90 秒。

只验证一张卡：

```bash
DURATION=60 GPU_LIST=0 bash run_gpu_proof.sh
```

验证八张卡两分钟：

```bash
DURATION=120 GPU_LIST=0,1,2,3,4,5,6,7 bash run_gpu_proof.sh
```

## 成功判定

`training_summary.json` 中应满足：

- `overall_status` 为 `PASS`；
- 每张 GPU 的 `status` 为 `PASS`；
- `steps > 0`；
- `parameter_changed` 为 `true`；
- 通常 `final_loss < first_loss`。

`gpu_monitor.log` 应包含训练期间的多次 `mthreads-gmi` 输出。

## 建议提交的证明材料

提交整个 `proof_<hostname>_<timestamp>.tar.gz`，同时截取：

1. `mthreads-gmi` 显示 S5000 型号和八张卡的画面；
2. 训练终端的 `FINAL SUMMARY`；
3. `gpu_monitor.log` 中训练进行时的显存/利用率记录；
4. `training_summary.csv`；
5. `SHA256SUMS.txt`。

## 常见问题

### `torch.musa.is_available()` 为 False

检查驱动、MUSA Runtime、Torch-MUSA、`LD_LIBRARY_PATH` 和容器设备映射。

### 显存不足

降低负载：

```bash
python musa_tiny_train.py \
  --duration 60 \
  --batch-size 128 \
  --hidden-dim 2048 \
  --output-dir proof_test
```

### 只希望证明“单卡可用”

```bash
DURATION=60 GPU_LIST=0 bash run_gpu_proof.sh
```

### 需要证明真正的 8 卡分布式训练

第一步先运行本证明包。确认每卡计算正常后，再单独验证 MCCL 和 DDP。
不要把 MCCL/DDP 作为第一份证明，因为通信配置失败并不代表 GPU 不能训练。
