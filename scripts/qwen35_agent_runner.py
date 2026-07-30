#!/usr/bin/env python3
"""Small deterministic model-plus-agent runner for the worker31008 pilot."""

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path


TOOL = {
    "type": "function",
    "function": {
        "name": "lookup_exchange_rate",
        "description": "Look up a fixed local exchange rate.",
        "parameters": {
            "type": "object",
            "properties": {
                "base_currency": {"type": "string"},
                "quote_currency": {"type": "string"},
            },
            "required": ["base_currency", "quote_currency"],
            "additionalProperties": False,
        },
    },
}

CASES = [
    ("USD", "EUR"),
    ("EUR", "CNY"),
    ("GBP", "USD"),
    ("JPY", "CNY"),
    ("CNY", "USD"),
]

FUNCTION_RE = re.compile(r"<function=([^>\n]+)>\s*(.*?)\s*</function>", re.S)
PARAMETER_RE = re.compile(r"<parameter=([^>\n]+)>\s*(.*?)\s*</parameter>", re.S)


def post(url, payload):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)


def extract_call(response):
    message = response["choices"][0]["message"]
    native = message.get("tool_calls") or []
    if native:
        call = native[0]
        args = call["function"].get("arguments", "{}")
        if isinstance(args, str):
            args = json.loads(args)
        return call["function"]["name"], args, message

    content = message.get("content") or ""
    function = FUNCTION_RE.search(content)
    if not function:
        return None, None, message
    args = {}
    for key, value in PARAMETER_RE.findall(function.group(2)):
        args[key.strip()] = value.strip()
    normalized_message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_normalized_0",
            "type": "function",
            "function": {
                "name": function.group(1).strip(),
                "arguments": json.dumps(args, ensure_ascii=False, sort_keys=True),
            },
        }],
    }
    return function.group(1).strip(), args, normalized_message


def run_case(endpoint, model, base, quote):
    messages = [{
        "role": "user",
        "content": f"Use the provided function to look up the exchange rate from {base} to {quote}.",
    }]
    first = post(endpoint, {
        "model": model,
        "messages": messages,
        "tools": [TOOL],
        "tool_choice": "auto",
        "temperature": 0,
        "seed": 0,
        "max_tokens": 256,
        "chat_template_kwargs": {"enable_thinking": False},
    })
    name, args, assistant = extract_call(first)
    expected = {"base_currency": base, "quote_currency": quote}
    name_ok = name == TOOL["function"]["name"]
    args_ok = args == expected
    final = None
    second = None
    if name_ok and args_ok:
        tool_result = {**expected, "rate": 0.92, "source": "fixed_agent_runner"}
        second = post(endpoint, {
            "model": model,
            "messages": messages + [assistant, {
                "role": "tool",
                "tool_call_id": assistant["tool_calls"][0]["id"],
                "content": json.dumps(tool_result, ensure_ascii=False),
            }],
            "tools": [TOOL],
            "temperature": 0,
            "seed": 0,
            "max_tokens": 256,
            "chat_template_kwargs": {"enable_thinking": False},
        })
        final = second["choices"][0]["message"].get("content") or ""
    return {
        "expected": expected,
        "tool_name_ok": name_ok,
        "arguments_ok": args_ok,
        "final_answer_ok": bool(final),
        "passed": bool(name_ok and args_ok and final),
        "first_response": first,
        "second_response": second,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    started = time.time()
    results = []
    for base, quote in CASES:
        try:
            results.append(run_case(args.endpoint, args.model, base, quote))
        except Exception as error:
            results.append({"expected": {"base_currency": base, "quote_currency": quote}, "error": repr(error), "passed": False})
    summary = {
        "label": args.label,
        "model": args.model,
        "benchmark": "agent-tool-call-pilot-v2",
        "seed": 0,
        "case_count": len(results),
        "passed": sum(bool(row.get("passed")) for row in results),
        "tool_selection_accuracy": sum(bool(row.get("tool_name_ok")) for row in results) / len(results),
        "argument_accuracy": sum(bool(row.get("arguments_ok")) for row in results) / len(results),
        "final_answer_rate": sum(bool(row.get("final_answer_ok")) for row in results) / len(results),
        "elapsed_seconds": round(time.time() - started, 3),
        "results": results,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("label", "case_count", "passed", "tool_selection_accuracy", "argument_accuracy", "final_answer_rate")}, ensure_ascii=False))
    print(f"output={output}")


if __name__ == "__main__":
    main()
