#!/usr/bin/env python3
"""
Short MUSA GPU training proof.

This script launches one independent training worker on every visible MUSA GPU.
Each worker performs real forward propagation, backward propagation, and
optimizer updates on a small neural network using synthetic data.

It intentionally avoids distributed collectives, so it can verify all GPUs
without depending on MCCL/DDP configuration.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import os
import platform
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def safe_call(func, default: Any = None) -> Any:
    try:
        return func()
    except Exception:
        return default


def tensor_digest(tensor: torch.Tensor) -> str:
    """Create a compact digest from a small CPU sample of a tensor."""
    sample = tensor.detach().flatten()[:2048].float().cpu().numpy().tobytes()
    return hashlib.sha256(sample).hexdigest()[:16]


def worker(
    rank: int,
    duration_s: int,
    batch_size: int,
    input_dim: int,
    hidden_dim: int,
    output_dim: int,
    log_every: int,
    result_queue: mp.Queue,
    output_dir: str,
) -> None:
    log_path = Path(output_dir) / f"gpu_{rank}.log"

    def log(message: str) -> None:
        line = f"[{utc_now()}] [GPU {rank}] {message}"
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    try:
        torch.musa.set_device(rank)
        device = torch.device(f"musa:{rank}")

        seed = 20260715 + rank
        torch.manual_seed(seed)
        safe_call(lambda: torch.musa.manual_seed(seed))

        device_name = safe_call(lambda: torch.musa.get_device_name(rank), f"musa:{rank}")
        props = safe_call(lambda: torch.musa.get_device_properties(rank), None)

        model = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, output_dim),
        ).to(device)

        optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3)
        criterion = nn.CrossEntropyLoss()

        # Fixed synthetic batch: the loss should visibly decrease, proving
        # that backward propagation and optimizer updates occurred.
        x = torch.randn(batch_size, input_dim, device=device)
        y = torch.randint(0, output_dim, (batch_size,), device=device)

        first_param = next(model.parameters())
        initial_digest = tensor_digest(first_param)
        initial_norm = float(first_param.detach().float().norm().cpu())

        # Warm-up.
        for _ in range(3):
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()
        safe_call(torch.musa.synchronize)

        start = time.monotonic()
        steps = 0
        first_loss = None
        last_loss = None

        total_mem_gb = None
        if props is not None and hasattr(props, "total_memory"):
            total_mem_gb = round(float(props.total_memory) / 1024**3, 2)

        log(
            f"START device={device_name!r}, total_memory_gb={total_mem_gb}, "
            f"batch={batch_size}, dims={input_dim}->{hidden_dim}->{hidden_dim}->{output_dim}"
        )

        while time.monotonic() - start < duration_s:
            optimizer.zero_grad(set_to_none=True)
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()

            steps += 1
            loss_value = float(loss.detach().cpu())
            if first_loss is None:
                first_loss = loss_value
            last_loss = loss_value

            if steps == 1 or steps % log_every == 0:
                elapsed = time.monotonic() - start
                allocated_gb = safe_call(
                    lambda: round(torch.musa.memory_allocated(rank) / 1024**3, 3),
                    None,
                )
                log(
                    f"step={steps}, loss={loss_value:.6f}, "
                    f"steps_per_sec={steps / max(elapsed, 1e-9):.3f}, "
                    f"allocated_gb={allocated_gb}"
                )

        safe_call(torch.musa.synchronize)
        elapsed = time.monotonic() - start

        final_digest = tensor_digest(first_param)
        final_norm = float(first_param.detach().float().norm().cpu())
        parameter_changed = initial_digest != final_digest

        result = {
            "rank": rank,
            "device_name": str(device_name),
            "total_memory_gb": total_mem_gb,
            "status": "PASS" if parameter_changed and steps > 0 else "FAIL",
            "steps": steps,
            "elapsed_seconds": round(elapsed, 3),
            "steps_per_second": round(steps / max(elapsed, 1e-9), 4),
            "first_loss": first_loss,
            "final_loss": last_loss,
            "loss_decreased": (
                bool(last_loss < first_loss)
                if first_loss is not None and last_loss is not None
                else False
            ),
            "initial_parameter_norm": initial_norm,
            "final_parameter_norm": final_norm,
            "initial_parameter_digest": initial_digest,
            "final_parameter_digest": final_digest,
            "parameter_changed": parameter_changed,
            "log_file": str(log_path),
        }
        log(
            f"END status={result['status']}, steps={steps}, "
            f"first_loss={first_loss:.6f}, final_loss={last_loss:.6f}, "
            f"parameter_changed={parameter_changed}"
        )
        result_queue.put(result)

    except Exception as exc:
        import traceback

        error = traceback.format_exc()
        log(f"ERROR {exc!r}\n{error}")
        result_queue.put(
            {
                "rank": rank,
                "status": "ERROR",
                "error": repr(exc),
                "traceback": error,
                "log_file": str(log_path),
            }
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=90)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--input-dim", type=int, default=2048)
    parser.add_argument("--hidden-dim", type=int, default=4096)
    parser.add_argument("--output-dim", type=int, default=256)
    parser.add_argument("--log-every", type=int, default=10)
    parser.add_argument("--num-gpus", type=int, default=0,
                        help="0 means all visible MUSA GPUs.")
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    musa_available = bool(safe_call(torch.musa.is_available, False))
    visible_count = int(safe_call(torch.musa.device_count, 0) or 0)

    if not musa_available or visible_count < 1:
        print(
            "ERROR: torch.musa is unavailable or no MUSA GPU is visible.\n"
            "Check the driver, MUSA runtime, torch_musa installation, "
            "LD_LIBRARY_PATH, and MUSA_VISIBLE_DEVICES.",
            file=sys.stderr,
        )
        return 2

    num_gpus = visible_count if args.num_gpus <= 0 else min(args.num_gpus, visible_count)

    torch_musa_version = None
    try:
        import torch_musa  # type: ignore
        torch_musa_version = getattr(torch_musa, "__version__", "unknown")
    except Exception:
        torch_musa_version = "imported implicitly or unavailable as module"

    metadata = {
        "start_time": utc_now(),
        "hostname": socket.gethostname(),
        "user": os.environ.get("USER", "unknown"),
        "platform": platform.platform(),
        "python_version": sys.version.replace("\n", " "),
        "torch_version": torch.__version__,
        "torch_musa_version": torch_musa_version,
        "musa_available": musa_available,
        "visible_gpu_count": visible_count,
        "launched_gpu_count": num_gpus,
        "musa_visible_devices": os.environ.get("MUSA_VISIBLE_DEVICES"),
        "training_config": {
            "duration_seconds": args.duration,
            "batch_size": args.batch_size,
            "input_dim": args.input_dim,
            "hidden_dim": args.hidden_dim,
            "output_dim": args.output_dim,
        },
    }

    print(json.dumps(metadata, ensure_ascii=False, indent=2), flush=True)

    ctx = mp.get_context("spawn")
    queue: mp.Queue = ctx.Queue()
    processes: list[mp.Process] = []

    for rank in range(num_gpus):
        p = ctx.Process(
            target=worker,
            args=(
                rank,
                args.duration,
                args.batch_size,
                args.input_dim,
                args.hidden_dim,
                args.output_dim,
                args.log_every,
                queue,
                str(output_dir),
            ),
        )
        p.start()
        processes.append(p)

    results = [queue.get() for _ in range(num_gpus)]

    for p in processes:
        p.join()

    results.sort(key=lambda item: item["rank"])
    metadata["end_time"] = utc_now()
    metadata["results"] = results
    metadata["overall_status"] = (
        "PASS" if all(item.get("status") == "PASS" for item in results) else "FAIL"
    )

    summary_path = output_dir / "training_summary.json"
    summary_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    csv_path = output_dir / "training_summary.csv"
    fields = [
        "rank", "device_name", "status", "steps", "elapsed_seconds",
        "steps_per_second", "first_loss", "final_loss", "loss_decreased",
        "parameter_changed", "initial_parameter_digest",
        "final_parameter_digest", "total_memory_gb",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    print("\n=== FINAL SUMMARY ===")
    for item in results:
        print(
            f"GPU {item['rank']}: {item.get('status')} | "
            f"device={item.get('device_name')} | "
            f"steps={item.get('steps')} | "
            f"loss={item.get('first_loss')} -> {item.get('final_loss')} | "
            f"parameter_changed={item.get('parameter_changed')}"
        )
    print(f"Overall: {metadata['overall_status']}")
    print(f"JSON: {summary_path}")
    print(f"CSV : {csv_path}")

    return 0 if metadata["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
