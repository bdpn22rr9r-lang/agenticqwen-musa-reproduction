#!/usr/bin/env python3
"""BFCL V4 Agentic adapter: Pi agent loop plus official Web Search/Memory backends."""
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path

from bfcl_eval.eval_checker.agentic_eval.agentic_checker import agentic_checker
from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import execute_multi_turn_func_call

FUNCTION_DOCS = {
    "WebSearchAPI": "web_search.json",
    "MemoryAPI_kv": "memory_kv.json",
    "MemoryAPI_vector": "memory_vector.json",
    "MemoryAPI_rec_sum": "memory_rec_sum.json",
}
MEMORY_PREREQ_FILES = (
    "memory_customer.json",
    "memory_finance.json",
    "memory_healthcare.json",
    "memory_notetaker.json",
    "memory_student.json",
)


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def schema(value):
    if isinstance(value, dict):
        return {key: schema(item) for key, item in value.items()}
    if isinstance(value, list):
        return [schema(item) for item in value]
    return value


def tool_list(root: Path, backend: str) -> list[dict]:
    docs = root / "bfcl_eval" / "data" / "multi_turn_func_doc" / FUNCTION_DOCS[backend]
    return [{
        "type": "function",
        "function": {
            "name": doc["name"],
            "description": doc.get("description", ""),
            "parameters": schema(doc.get("parameters", {"type": "object", "properties": {}})),
        },
    } for doc in rows(docs)]


def load_source(root: Path, category: dict) -> tuple[list[dict], dict[str, list[str]]]:
    data = root / "bfcl_eval" / "data"
    entries = rows(data / category["task_file"])
    answers = {item["id"]: item["ground_truth"] for item in rows(data / "possible_answer" / category["answer_file"])}
    return entries, answers


def prereq_for(root: Path, scenario: str) -> list[dict]:
    directory = root / "bfcl_eval" / "data" / "memory_prereq_conversation"
    for filename in MEMORY_PREREQ_FILES:
        candidate = directory / filename
        if not candidate.is_file():
            continue
        entries = rows(candidate)
        selected = [entry for entry in entries if entry.get("scenario") == scenario]
        if selected:
            return sorted(selected, key=lambda item: item["id"])
    raise FileNotFoundError(f"memory prerequisite scenario not found: {scenario}")


def initial_config(category: dict, entry: dict, output: Path, task_id: str) -> dict:
    backend = category["backend"]
    if backend == "WebSearchAPI":
        return {backend: {"show_snippet": bool(category["show_snippet"])}}
    scenario = entry.get("scenario") or entry.get("initial_config", {}).get("scenario")
    if not scenario:
        raise ValueError(f"memory task has no scenario: {entry['id']}")
    return {backend: {
        "model_result_dir": str(output),
        "test_id": task_id,
        "scenario": scenario,
    }}


def question_turns(question) -> list[list[dict]]:
    if isinstance(question, str):
        return [[{"role": "user", "content": question}]]
    if not isinstance(question, list):
        raise TypeError(f"unsupported question shape: {type(question).__name__}")
    if not question:
        return [[]]
    if isinstance(question[0], str):
        return [[{"role": "user", "content": item} for item in question]]
    if isinstance(question[0], dict):
        return [question]
    return question


def build_input(root: Path, output: Path, category: dict, entry: dict, provider: str, model: str, args) -> dict:
    backend = category["backend"]
    sessions = []
    if backend.startswith("MemoryAPI_"):
        scenario = entry.get("scenario") or entry.get("initial_config", {}).get("scenario")
        for prereq in prereq_for(root, scenario):
            sessions.append({
                "task_id": prereq["id"],
                "question": question_turns(prereq["question"]),
                "initial_config": initial_config(category, entry, output, prereq["id"]),
                "involved_classes": [backend],
                "flush": True,
            })
    sessions.append({
        "task_id": entry["id"],
        "question": question_turns(entry["question"]),
        "initial_config": initial_config(category, entry, output, entry["id"]),
        "involved_classes": [backend],
        "flush": False,
    })
    return {
        "id": entry["id"],
        "category": category["id"],
        "entry": entry,
        "tools": tool_list(root, backend),
        "sessions": sessions,
        "provider": provider,
        "model": model,
        "maxStepsPerTurn": args.max_steps,
        "maxStepsPerSession": args.max_session_steps,
        "maxStepsPerTask": args.max_task_steps,
        "timeoutSeconds": args.timeout_seconds,
    }


def assistant_answer(pi_result: dict) -> str:
    values = [item.get("text", "") for item in pi_result.get("assistant_responses", [])]
    return values[-1] if values else ""


def execute_once(request: dict) -> dict:
    text = request["name"] + "(" + ",".join(f"{key}={value!r}" for key, value in request["arguments"].items()) + ")"
    config = json.loads(json.dumps(request["initial_config"]))
    for class_config in config.values():
        if isinstance(class_config, dict) and "model_result_dir" in class_config:
            class_config["model_result_dir"] = Path(class_config["model_result_dir"])
    result, instances = execute_multi_turn_func_call(
        [text], config, request["involved_classes"], request["model"], request["task_id"],
        long_context=request.get("long_context", False), is_evaL_run=True,
    )
    return {"content": str(result[0]) if result else "", "instances": instances, "call_text": text}


def serve() -> None:
    instances_by_task = {}
    for line in os.sys.stdin:
        request = json.loads(line)
        if request.get("op") == "flush":
            instances = instances_by_task.get(request["task_id"], {})
            try:
                for instance in instances.values():
                    flush = getattr(instance, "_flush_memory_to_local_file", None)
                    if flush is not None:
                        flush()
                print(json.dumps({"request_id": request["request_id"], "flushed": True}), flush=True)
            except Exception as error:
                print(json.dumps({"request_id": request["request_id"], "error": repr(error)}), flush=True)
            continue
        try:
            response = execute_once(request)
            instances_by_task[request["task_id"]] = response.pop("instances", {})
            response["request_id"] = request["request_id"]
        except Exception as error:
            response = {"request_id": request["request_id"], "error": repr(error)}
        print(json.dumps(response, ensure_ascii=False, default=str), flush=True)


def write_jsonl(path: Path, value: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")


def run(args):
    root, out = Path(args.source), Path(args.output)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"output exists: {out}")
    out.mkdir(parents=True)
    config = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    selected = [item for item in config["categories"] if not args.category or item["id"] == args.category]
    if not selected:
        raise ValueError(f"unknown category: {args.category}")
    all_entries = []
    for category in selected:
        entries, answers = load_source(root, category)
        if len(entries) != category["count"] or len(answers) != category["count"]:
            raise ValueError(f"count gate failed for {category['id']}: {len(entries)} tasks/{len(answers)} answers")
        for entry in entries:
            all_entries.append((category, entry, answers[entry["id"]]))
    if args.task_id:
        all_entries = [item for item in all_entries if item[1]["id"] == args.task_id]
    if args.limit is not None:
        all_entries = all_entries[:args.limit]
    if not all_entries:
        raise ValueError("no selected BFCL Agentic tasks")
    if any(item["backend"] == "WebSearchAPI" for item in selected) and not os.environ.get("SERPAPI_API_KEY"):
        raise RuntimeError("AGENTIC_WEB_SEARCH_KEY_MISSING: set SERPAPI_API_KEY without writing it to a command or manifest")
    if any(item["backend"] == "MemoryAPI_vector" for item in selected):
        for dependency in ("faiss", "sentence_transformers"):
            if importlib.util.find_spec(dependency) is None:
                raise RuntimeError(f"AGENTIC_VECTOR_DEPENDENCY_MISSING: {dependency}")
    raw, traces, results = (out / name for name in ("raw_events.jsonl", "tool_traces.jsonl", "task_results.jsonl"))
    runner = Path(args.runner)
    source_inputs = [root / "bfcl_eval" / "data" / item["task_file"] for item in selected]
    source_inputs += [root / "bfcl_eval" / "data" / "possible_answer" / item["answer_file"] for item in selected]
    source_inputs += [root / "bfcl_eval" / "data" / "multi_turn_func_doc" / FUNCTION_DOCS[item["backend"]] for item in selected]
    source_inputs += sorted((root / "bfcl_eval" / "data" / "memory_prereq_conversation").glob("*.json"))
    manifest = {
        "benchmark": "BFCL-V4 Agentic",
        "agentic_total": 665,
        "selected_categories": [item["id"] for item in selected],
        "selected_tasks": len(all_entries),
        "agent_runtime": "Pi 0.83.0",
        "provider": args.provider,
        "model": args.model,
        "max_steps_per_turn": args.max_steps,
        "max_steps_per_session": args.max_session_steps,
        "max_steps_per_task": args.max_task_steps,
        "timeout_seconds": args.timeout_seconds,
        "adapter_sha256": sha256(Path(__file__).resolve()),
        "pi_task_runner_sha256": sha256(runner),
        "official_checker": "bfcl_eval.eval_checker.agentic_eval.agentic_checker.agentic_checker",
        "source_inputs": [{"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": sha256(path)} for path in sorted(set(source_inputs))],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    environment = os.environ.copy()
    environment.update({"PI_APP": args.pi_app, "PI_MODELS": args.pi_models, "PI_AGENT_DIR": args.pi_agent_dir, "PI_AUTH": args.pi_auth, "PI_EXECUTOR_PY": str(Path(__file__).resolve())})
    passed = 0
    for category, entry, answers in all_entries:
        bundle = out / f"{category['id']}_{entry['id']}.input.json"
        node_result = out / f"{category['id']}_{entry['id']}.pi.json"
        try:
            bundle.write_text(json.dumps(build_input(root, out, category, entry, args.provider, args.model, args), ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run([args.node, str(runner), "--input", str(bundle), "--output", str(node_result)], env=environment, capture_output=True, text=True, timeout=args.timeout_seconds * max(1, args.max_task_steps))
            if completed.returncode:
                raise RuntimeError(f"PI_TASK_FAILED {entry['id']}: {completed.stderr[-2000:]}")
            pi_result = json.loads(node_result.read_text(encoding="utf-8"))
            for event in pi_result.get("events", []):
                write_jsonl(raw, {"id": entry["id"], "category": category["id"], "event": event})
            for index, calls in enumerate(pi_result.get("calls_by_session", [])):
                write_jsonl(traces, {"id": entry["id"], "category": category["id"], "session": index, "calls": calls})
            checked = agentic_checker(assistant_answer(pi_result), answers)
            valid = bool(checked.get("valid"))
            passed += valid
            write_jsonl(results, {"id": entry["id"], "category": category["id"], "valid": valid, "checker": checked, "runtime_failure": False, "assistant_answer": assistant_answer(pi_result), "total_calls": pi_result.get("total_calls", 0)})
        except Exception as error:
            failure = {"id": entry["id"], "category": category["id"], "runtime_failure": True, "error_type": "runtime:agentic_runner_error", "errors": [str(error)]}
            write_jsonl(results, failure)
            (out / "FAILED").write_text(json.dumps(failure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            raise
    scores = {"benchmark": "BFCL_V4_AGENTIC", "task_count": len(all_entries), "passed": passed, "valid_rate": passed / len(all_entries), "runtime_failures": 0}
    (out / "scores.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    (out / "summary.md").write_text(f"# BFCL V4 Agentic Pi Run\n\nmodel: {args.model}\ntasks: {len(all_entries)}\npassed: {passed}\nvalid_rate: {scores['valid_rate']:.6f}\n", encoding="utf-8")
    (out / "COMPLETE").write_text("COMPLETE=PASS\nbenchmark=BFCL_V4_AGENTIC\n", encoding="utf-8")
    checksums = [f"{sha256(file)}  {file.name}" for file in sorted(out.iterdir()) if file.is_file() and file.name != "sha256sum.txt"]
    (out / "sha256sum.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    print("\n".join(checksums))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--source")
    parser.add_argument("--plan", required=False, default=str(Path(__file__).resolve().parents[1] / "configs" / "bfcl_v4_agentic_plan.json"))
    parser.add_argument("--provider")
    parser.add_argument("--model")
    parser.add_argument("--output")
    parser.add_argument("--category")
    parser.add_argument("--task-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-session-steps", type=int, default=64)
    parser.add_argument("--max-task-steps", type=int, default=1024)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--node", default="/workspace/qwen35/formal-bench/pi-runtime/node/bin/node")
    parser.add_argument("--runner", default=str(Path(__file__).with_name("pi_bfcl_agentic_task_runner.mjs")))
    parser.add_argument("--pi-app", default="/workspace/qwen35/formal-bench/pi-runtime/app")
    parser.add_argument("--pi-models", default="/workspace/qwen35/formal-bench/pi-runtime/home/.pi/agent/models.json")
    parser.add_argument("--pi-agent-dir", default="/workspace/qwen35/formal-bench/pi-runtime/home/.pi/agent")
    parser.add_argument("--pi-auth", default="/workspace/qwen35/formal-bench/pi-runtime/home/.pi/agent/auth.json")
    args = parser.parse_args()
    if args.serve:
        serve()
        return
    for name in ("source", "provider", "model", "output"):
        if not getattr(args, name):
            parser.error(f"--{name.replace('_', '-')} is required")
    run(args)


if __name__ == "__main__":
    main()
