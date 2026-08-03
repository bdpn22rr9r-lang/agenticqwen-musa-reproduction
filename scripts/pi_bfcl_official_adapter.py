#!/usr/bin/env python3
"""BFCL-V4 adapter: Pi runs the agent loop; official BFCL executes and scores."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from bfcl_eval.constants.executable_backend_config import MULTI_TURN_FUNC_DOC_FILE_MAPPING
from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker import multi_turn_checker
from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import execute_multi_turn_func_call


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def schema(value):
    if isinstance(value, dict):
        result = {key: schema(item) for key, item in value.items()}
        return result
    if isinstance(value, list):
        return [schema(item) for item in value]
    return value


def tool_list(root: Path, entry: dict) -> list[dict]:
    docs = root / "bfcl_eval" / "data" / "multi_turn_func_doc"
    result = []
    for class_name in entry["involved_classes"]:
        for doc in rows(docs / MULTI_TURN_FUNC_DOC_FILE_MAPPING[class_name]):
            result.append({"type": "function", "function": {"name": doc["name"], "description": doc.get("description", ""), "parameters": schema(doc.get("parameters", {"type": "object", "properties": {}}))}})
    return result


def call_text(name: str, arguments: dict) -> str:
    return name + "(" + ",".join(f"{key}={value!r}" for key, value in arguments.items()) + ")"


def execute_once(request: dict) -> dict:
    text = call_text(request["name"], request["arguments"])
    result, config = execute_multi_turn_func_call(
        [text], request["config"], request["involved_classes"], request["model"], request["task_id"],
        long_context=request["long_context"], is_evaL_run=True,
    )
    return {"content": str(result[0]) if result else "", "config": config, "call_text": text}


def serve() -> None:
    states = {}
    for line in sys.stdin:
        request = json.loads(line)
        key = request["task_id"]
        request["config"] = states.get(key, request["initial_config"])
        try:
            response = execute_once(request)
            states[key] = response.pop("config")
            response["request_id"] = request["request_id"]
        except Exception as error:
            response = {"request_id": request["request_id"], "error": repr(error)}
        print(json.dumps(response, ensure_ascii=False, default=str), flush=True)


def load(root: Path, task_id: str | None, limit: int | None):
    data = root / "bfcl_eval" / "data"
    entries, answers = [], {}
    for category in ("base", "miss_func", "miss_param", "long_context"):
        entries.extend(rows(data / f"BFCL_v4_multi_turn_{category}.json"))
        answers.update({item["id"]: item["ground_truth"] for item in rows(data / "possible_answer" / f"BFCL_v4_multi_turn_{category}.json")})
    if task_id:
        entries = [entry for entry in entries if entry["id"] == task_id]
    if limit is not None:
        entries = entries[:limit]
    if not entries:
        raise ValueError("no selected BFCL tasks")
    return entries, answers


def write_jsonl(path: Path, value: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")


def run(args):
    root, out = Path(args.source), Path(args.output)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"output exists: {out}")
    out.mkdir(parents=True)
    entries, answers = load(root, args.task_id, args.limit)
    raw, traces, results = (out / name for name in ("raw_events.jsonl", "tool_traces.jsonl", "task_results.jsonl"))
    runner = Path(args.runner)
    if not runner.is_file():
        raise FileNotFoundError(runner)
    node = args.node
    data = root / "bfcl_eval" / "data"
    source_inputs = [
        data / f"BFCL_v4_multi_turn_{category}.json"
        for category in ("base", "miss_func", "miss_param", "long_context")
    ] + [
        data / "possible_answer" / f"BFCL_v4_multi_turn_{category}.json"
        for category in ("base", "miss_func", "miss_param", "long_context")
    ] + sorted((data / "multi_turn_func_doc").glob("*.json"))
    manifest = {
        "benchmark": "BFCL-V4 Multi-turn",
        "agent_runtime": "Pi 0.83.0",
        "provider": args.provider,
        "model": args.model,
        "task_id": args.task_id,
        "limit": args.limit,
        "max_steps": args.max_steps,
        "timeout_seconds": args.timeout_seconds,
        "adapter_sha256": sha256(Path(__file__).resolve()),
        "pi_task_runner_sha256": sha256(runner),
        "source_inputs": [
            {"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": sha256(path)}
            for path in source_inputs
        ],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    environment = os.environ.copy()
    environment.update({"PI_APP": args.pi_app, "PI_MODELS": args.pi_models, "PI_AGENT_DIR": args.pi_agent_dir, "PI_AUTH": args.pi_auth, "PI_EXECUTOR_PY": str(Path(__file__).resolve())})
    passed = 0
    for entry in entries:
        category = entry["id"].rsplit("_", 1)[0]
        bundle = out / f"{entry['id']}.input.json"
        node_result = out / f"{entry['id']}.pi.json"
        bundle.write_text(json.dumps({"entry": entry, "category": category, "tools": tool_list(root, entry), "provider": args.provider, "model": args.model, "maxSteps": args.max_steps, "timeoutSeconds": args.timeout_seconds}), encoding="utf-8")
        completed = subprocess.run([node, str(runner), "--input", str(bundle), "--output", str(node_result)], env=environment, capture_output=True, text=True, timeout=args.timeout_seconds * max(1, args.max_steps))
        if completed.returncode:
            raise RuntimeError(f"PI_TASK_FAILED {entry['id']}: {completed.stderr[-2000:]}")
        pi_result = json.loads(node_result.read_text(encoding="utf-8"))
        for event in pi_result["events"]:
            write_jsonl(raw, {"id": entry["id"], "event": event})
        decoded = []
        for turn, calls in enumerate(pi_result["calls_by_turn"]):
            decoded.append([[call["call_text"] for call in calls]] if calls else [[]])
            write_jsonl(traces, {"id": entry["id"], "turn": turn, "calls": calls})
        checked = multi_turn_checker(decoded, answers[entry["id"]], entry, category, args.model)
        passed += bool(checked.get("valid"))
        write_jsonl(results, {"id": entry["id"], "category": category, "valid": bool(checked.get("valid")), "checker": checked, "trajectory": decoded})
    scores = {"task_count": len(entries), "passed": passed, "valid_rate": passed / len(entries)}
    (out / "scores.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    (out / "summary.md").write_text(
        f"# BFCL Pi Run\n\nmodel: {args.model}\ntasks: {len(entries)}\npassed: {passed}\nvalid_rate: {scores['valid_rate']:.6f}\n",
        encoding="utf-8",
    )
    (out / "COMPLETE").write_text("COMPLETE=PASS\nbenchmark=BFCL_V4_MULTI_TURN\n", encoding="utf-8")
    checksums = [f"{sha256(file)}  {file.name}" for file in sorted(out.iterdir()) if file.is_file() and file.name != "sha256sum.txt"]
    (out / "sha256sum.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    print("\n".join(checksums))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--source")
    parser.add_argument("--provider")
    parser.add_argument("--model")
    parser.add_argument("--output")
    parser.add_argument("--task-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--node", default="/workspace/qwen35/formal-bench/pi-runtime/node/bin/node")
    parser.add_argument("--runner", default=str(Path(__file__).with_name("pi_bfcl_task_runner.mjs")))
    parser.add_argument("--pi-app", default="/workspace/qwen35/formal-bench/pi-runtime/app")
    parser.add_argument("--pi-models", default="/workspace/qwen35/formal-bench/pi-runtime/home/.pi/agent/models.json")
    parser.add_argument("--pi-agent-dir", default="/workspace/qwen35/formal-bench/pi-runtime/home/.pi/agent")
    parser.add_argument("--pi-auth", default="/workspace/qwen35/formal-bench/pi-runtime/home/.pi/agent/auth.json")
    args = parser.parse_args()
    if args.execute:
        print(json.dumps(execute_once(json.load(sys.stdin)), ensure_ascii=False, default=str))
        return
    if args.serve:
        serve()
        return
    for name in ("source", "provider", "model", "output"):
        if not getattr(args, name):
            parser.error(f"--{name.replace('_', '-')} is required")
    run(args)


if __name__ == "__main__":
    main()
