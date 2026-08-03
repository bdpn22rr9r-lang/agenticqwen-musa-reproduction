#!/usr/bin/env python3
"""Auditable OpenAI-compatible model-plus-agent runtime.

Benchmark adapters own data and scoring.  This module only sends requests,
normalizes actual model tool-call output, executes an optional local tool, and
returns the complete request/response trace.
"""

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Callable


ToolExecutor = Callable[[str, dict], str]
FUNCTION_RE = re.compile(r"<function=([^>\n]+)>\s*(.*?)\s*</function>", re.S)
PARAMETER_RE = re.compile(r"<parameter=([^>\n]+)>\s*(.*?)\s*</parameter>", re.S)


@dataclass
class RuntimeConfig:
    max_steps: int = 8
    timeout_seconds: int = 180
    temperature: float = 0.0
    seed: int = 0
    max_tokens: int = 256
    enable_thinking: bool = False


class RuntimeRequestError(RuntimeError):
    """A transport error with enough detail to preserve it in a trace."""

    def __init__(self, message: str, *, status_code: int | None = None, body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.body = body

    def as_dict(self) -> dict:
        return {"type": type(self).__name__, "message": str(self), "status_code": self.status_code, "body": self.body}


class UnifiedAgentRuntime:
    """One deterministic model-tool loop with durable, inspectable evidence."""

    def __init__(self, endpoint: str, model: str, executor: ToolExecutor | None = None,
                 config: RuntimeConfig | None = None):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.executor = executor
        self.config = config or RuntimeConfig()

    def _post(self, payload: dict) -> dict:
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeRequestError(f"HTTP {error.code}: {error.reason}", status_code=error.code, body=body) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise RuntimeRequestError(str(error)) from error

    @staticmethod
    def normalize_tool_calls(message: dict) -> dict:
        """Normalize only native calls or complete Qwen markup; never invent calls."""
        native = message.get("tool_calls") or []
        if native:
            calls = []
            for index, call in enumerate(native):
                function = call.get("function") or {}
                name = function.get("name")
                arguments = function.get("arguments", "{}")
                if not isinstance(name, str) or not name.strip():
                    return {"mode": "invalid_native", "calls": [], "error": f"call {index} has no function name"}
                if isinstance(arguments, dict):
                    arguments = json.dumps(arguments, ensure_ascii=False, sort_keys=True)
                if not isinstance(arguments, str):
                    return {"mode": "invalid_native", "calls": [], "error": f"call {index} has non-string arguments"}
                try:
                    json.loads(arguments)
                except json.JSONDecodeError as error:
                    return {"mode": "invalid_native", "calls": [], "error": f"call {index} arguments are not JSON: {error.msg}"}
                calls.append({"id": call.get("id") or f"call_{index}", "type": "function", "function": {"name": name.strip(), "arguments": arguments}})
            return {"mode": "native_tool_calls", "calls": calls, "error": None}

        content = message.get("content") or ""
        if "<function=" not in content:
            return {"mode": "none", "calls": [], "error": None}
        match = FUNCTION_RE.search(content)
        if not match:
            return {"mode": "invalid_qwen_markup", "calls": [], "error": "function markup is incomplete"}
        arguments = {}
        for key, value in PARAMETER_RE.findall(match.group(2)):
            arguments[key.strip()] = value.strip()
        return {
            "mode": "qwen_markup",
            "calls": [{"id": "call_normalized_0", "type": "function", "function": {"name": match.group(1).strip(), "arguments": json.dumps(arguments, ensure_ascii=False, sort_keys=True)}}],
            "error": None,
        }

    @staticmethod
    def assistant_history_message(message: dict, calls: list[dict]) -> dict:
        """Use only OpenAI-compatible assistant fields in the next request."""
        clean = {"role": "assistant", "content": message.get("content") or ""}
        if calls:
            clean["content"] = None
            clean["tool_calls"] = calls
        return clean

    @staticmethod
    def tool_message(call: dict, result: str) -> dict:
        return {"role": "tool", "tool_call_id": call["id"], "name": call["function"]["name"], "content": result}

    def request_payload(self, messages: list[dict], tools: list[dict]) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": self.config.temperature,
            "seed": self.config.seed,
            "max_tokens": self.config.max_tokens,
            "chat_template_kwargs": {"enable_thinking": self.config.enable_thinking},
        }

    def run_turn(self, messages: list[dict], tools: list[dict]) -> dict:
        """Run one user turn; the caller owns cross-turn conversation history."""
        history = list(messages)
        trace = []
        emitted_tool_calls = []
        started = time.time()
        for step in range(self.config.max_steps):
            payload = self.request_payload(history, tools)
            try:
                response = self._post(payload)
                message = response["choices"][0]["message"]
            except (KeyError, IndexError, TypeError, RuntimeRequestError) as error:
                trace.append({"step": step, "request": payload, "response": None, "error": error.as_dict() if isinstance(error, RuntimeRequestError) else {"type": type(error).__name__, "message": str(error)}})
                return {"status": "request_error", "messages": history, "assistant_message": None, "tool_calls": [], "emitted_tool_calls": emitted_tool_calls, "parse": {"mode": "request_error", "calls": [], "error": str(error)}, "trace": trace, "elapsed_seconds": round(time.time() - started, 3)}

            parsed = self.normalize_tool_calls(message)
            calls = parsed["calls"]
            emitted_tool_calls.extend(calls)
            record = {"step": step, "request": payload, "response": response, "parse": parsed}
            trace.append(record)
            assistant = self.assistant_history_message(message, calls)
            history.append(assistant)

            if not calls or self.executor is None:
                return {"status": "tool_calls_emitted" if calls else "completed", "messages": history, "assistant_message": assistant, "tool_calls": calls, "emitted_tool_calls": emitted_tool_calls, "parse": parsed, "trace": trace, "elapsed_seconds": round(time.time() - started, 3)}

            for call in calls:
                try:
                    arguments = json.loads(call["function"]["arguments"])
                    result = self.executor(call["function"]["name"], arguments)
                except Exception as error:  # The adapter preserves the exact local-tool failure.
                    record.setdefault("tool_execution", []).append({"call": call, "error": {"type": type(error).__name__, "message": str(error)}})
                    return {"status": "tool_execution_error", "messages": history, "assistant_message": assistant, "tool_calls": calls, "emitted_tool_calls": emitted_tool_calls, "parse": parsed, "trace": trace, "elapsed_seconds": round(time.time() - started, 3)}
                record.setdefault("tool_execution", []).append({"call": call, "result": result})
                history.append(self.tool_message(call, result))

        return {"status": "max_steps_exceeded", "messages": history, "assistant_message": None, "tool_calls": [], "emitted_tool_calls": emitted_tool_calls, "parse": {"mode": "max_steps_exceeded", "calls": [], "error": None}, "trace": trace, "elapsed_seconds": round(time.time() - started, 3)}


if __name__ == "__main__":
    markup = {"content": "<function=lookup>\n<parameter=currency>\nUSD\n</parameter>\n</function>"}
    parsed = UnifiedAgentRuntime.normalize_tool_calls(markup)
    assert parsed["mode"] == "qwen_markup"
    assert json.loads(parsed["calls"][0]["function"]["arguments"]) == {"currency": "USD"}
    assert asdict(RuntimeConfig())["max_steps"] == 8
    print("UNIFIED_AGENT_RUNTIME=OK")
