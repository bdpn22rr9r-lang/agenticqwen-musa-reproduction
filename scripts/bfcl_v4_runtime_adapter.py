#!/usr/bin/env python3
"""Auditable BFCL-V4 Multi-turn adapter using the official checker.

Generation always uses tool_choice=auto.  BFCL ground truth is used only by
the official checker after generation, never to influence an API request.
"""

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from unified_agent_runtime import RuntimeConfig, UnifiedAgentRuntime
from bfcl_eval.constants.category_mapping import MULTI_TURN_FUNC_DOC_FILE_MAPPING
from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker import multi_turn_checker
from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import execute_multi_turn_func_call


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_jsonl(handle, record: dict) -> None:
    handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    handle.flush()


def schema_type(value):
    aliases = {"dict": "object", "float": "number", "int": "integer", "bool": "boolean"}
    if isinstance(value, dict):
        value = dict(value)
        if "type" in value:
            value["type"] = aliases.get(value["type"], value["type"])
        if "properties" in value:
            value["properties"] = {key: schema_type(item) for key, item in value["properties"].items()}
        if "items" in value:
            value["items"] = schema_type(value["items"])
    return aliases.get(value, value)


def data_root(source: Path) -> Path:
    return source / "bfcl_eval" / "data" if (source / "bfcl_eval" / "data").is_dir() else source / "data"


def load_tools(root: Path, entry: dict) -> list[dict]:
    docs = data_root(root) / "multi_turn_func_doc"
    tools = []
    for class_name in entry["involved_classes"]:
        path = docs / MULTI_TURN_FUNC_DOC_FILE_MAPPING[class_name]
        if not path.is_file():
            raise FileNotFoundError(path)
        for doc in jsonl(path):
            tools.append({"type": "function", "function": {"name": doc["name"], "description": doc.get("description", ""), "parameters": schema_type(doc.get("parameters", {"type": "object", "properties": {}}))}})
    if not tools:
        raise ValueError(f"no BFCL tools for {entry['id']}")
    return tools


def call_text(call: dict) -> str:
    arguments = json.loads(call["function"]["arguments"])
    return call["function"]["name"] + "(" + ",".join(f"{key}={value!r}" for key, value in arguments.items()) + ")"


def make_executor(entry: dict, category: str, model: str):
    def execute(name: str, arguments: dict) -> str:
        text = name + "(" + ",".join(f"{key}={value!r}" for key, value in arguments.items()) + ")"
        result, _ = execute_multi_turn_func_call([text], entry["initial_config"], entry["involved_classes"], model, entry["id"], long_context="long_context" in category, is_evaL_run=True)
        return str(result[0]) if result else ""
    return execute


def run_task(root: Path, entry: dict, ground_truth: list, runtime: UnifiedAgentRuntime, raw_file, trace_file) -> dict:
    category = entry["id"].rsplit("_", 1)[0]
    tools = load_tools(root, entry)
    runtime.executor = make_executor(entry, category, runtime.model)
    history = []
    decoded = []
    started = time.time()
    statuses = []

    for turn_index, turn in enumerate(entry["question"]):
        outcome = runtime.run_turn(history + turn, tools)
        statuses.append(outcome["status"])
        for event in outcome["trace"]:
            write_jsonl(raw_file, {"id": entry["id"], "category": category, "turn": turn_index, **event})
        calls = outcome["emitted_tool_calls"]
        decoded.append([[call_text(call) for call in calls]] if calls else [[]])
        write_jsonl(trace_file, {"id": entry["id"], "category": category, "turn": turn_index, "status": outcome["status"], "parse_modes": [event.get("parse", {}).get("mode") for event in outcome["trace"]], "calls": calls})
        history = outcome["messages"]
        if outcome["status"] not in {"completed", "tool_calls_emitted"}:
            break

    if len(decoded) < len(entry["question"]):
        decoded.extend([[]] * (len(entry["question"]) - len(decoded)))
    checked = multi_turn_checker(decoded, ground_truth, entry, category, runtime.model)
    return {"id": entry["id"], "category": category, "valid": bool(checked.get("valid")), "checker": checked, "trajectory": decoded, "turn_statuses": statuses, "elapsed_seconds": round(time.time() - started, 3)}


def load_tasks(root: Path, task_id: str | None, limit: int | None) -> tuple[list[dict], dict, list[Path]]:
    data = data_root(root)
    entries, answers, inputs = [], {}, []
    for category in ("base", "miss_func", "miss_param", "long_context"):
        task_path = data / f"BFCL_v4_multi_turn_{category}.json"
        answer_path = data / "possible_answer" / f"BFCL_v4_multi_turn_{category}.json"
        inputs.extend((task_path, answer_path))
        entries.extend(jsonl(task_path))
        answers.update({row["id"]: row["ground_truth"] for row in jsonl(answer_path)})
    inputs.extend(sorted((data / "multi_turn_func_doc").glob("*.json")))
    if task_id:
        entries = [entry for entry in entries if entry["id"] == task_id]
        if len(entries) != 1:
            raise ValueError(f"task id not found: {task_id}")
    if limit is not None:
        entries = entries[:limit]
    return entries, answers, inputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--task-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-consecutive-errors", type=int, default=3)
    args = parser.parse_args()

    root, out = Path(args.source), Path(args.output)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing to overwrite nonempty output directory: {out}")
    out.mkdir(parents=True, exist_ok=True)
    entries, answers, inputs = load_tasks(root, args.task_id, args.limit)
    config = RuntimeConfig(max_steps=args.max_steps, timeout_seconds=args.timeout_seconds, max_tokens=args.max_tokens)
    runtime = UnifiedAgentRuntime(args.endpoint, args.model, config=config)
    manifest = {"benchmark": "BFCL-V4 Multi-turn", "model": args.model, "endpoint": args.endpoint, "runtime_config": asdict(config), "task_id": args.task_id, "limit": args.limit, "tool_choice": "auto", "source_inputs": [{"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": sha256(path)} for path in inputs], "runtime_sha256": sha256(Path(__file__).with_name("unified_agent_runtime.py")), "adapter_sha256": sha256(Path(__file__))}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    results, consecutive_errors = [], 0
    with (out / "task_results.jsonl").open("w", encoding="utf-8") as task_file, (out / "tool_traces.jsonl").open("w", encoding="utf-8") as trace_file, (out / "raw_responses.jsonl").open("w", encoding="utf-8") as raw_file:
        for index, entry in enumerate(entries, 1):
            result = run_task(root, entry, answers[entry["id"]], runtime, raw_file, trace_file)
            write_jsonl(task_file, result)
            results.append(result)
            consecutive_errors = consecutive_errors + 1 if any(status.endswith("error") for status in result["turn_statuses"]) else 0
            print(f"progress={index}/{len(entries)} passed={sum(row['valid'] for row in results)}", flush=True)
            if consecutive_errors >= args.max_consecutive_errors:
                break

    raw_response_count = sum(
        json.loads(line).get("response") is not None
        for line in (out / "raw_responses.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    summary = {"benchmark": "BFCL-V4 Multi-turn", "model": args.model, "requested_task_count": len(entries), "completed_task_count": len(results), "passed": sum(row["valid"] for row in results), "score": (sum(row["valid"] for row in results) / len(results)) if results else 0.0, "raw_response_count": raw_response_count, "status": "complete" if len(results) == len(entries) else "stopped_after_request_errors"}
    (out / "scores.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    sha_lines = [f"{sha256(path)}  {path.name}" for path in sorted(out.iterdir()) if path.is_file() and path.name not in {"sha256sum.txt", "COMPLETE"}]
    (out / "sha256sum.txt").write_text("\n".join(sha_lines) + "\n", encoding="utf-8")
    if summary["status"] == "complete":
        (out / "COMPLETE").write_text("BFCL_V4_COMPLETE\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
