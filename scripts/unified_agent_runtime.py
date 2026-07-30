#!/usr/bin/env python3
"""Deterministic OpenAI-compatible agent loop shared by all formal evals."""

import json
import time
import urllib.request
from dataclasses import dataclass
from typing import Callable


ToolExecutor = Callable[[str, dict], str]


@dataclass
class RuntimeConfig:
    max_steps: int = 8
    timeout_seconds: int = 180
    temperature: float = 0.0
    seed: int = 0


class UnifiedAgentRuntime:
    """One controlled model-tool loop; benchmark adapters supply tasks/tools."""

    def __init__(self, endpoint: str, model: str, executor: ToolExecutor,
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
        with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
            return json.load(response)

    def run(self, messages: list[dict], tools: list[dict]) -> dict:
        history = list(messages)
        trajectory = []
        started = time.time()

        for step in range(self.config.max_steps):
            response = self._post({
                "model": self.model,
                "messages": history,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": self.config.temperature,
                "seed": self.config.seed,
                "max_tokens": 2048,
                "chat_template_kwargs": {"enable_thinking": False},
            })
            message = response["choices"][0]["message"]
            record = {"step": step, "response": response}
            calls = message.get("tool_calls") or []
            history.append(message)

            if not calls:
                trajectory.append(record)
                return {
                    "status": "completed",
                    "answer": message.get("content") or "",
                    "steps": step + 1,
                    "elapsed_seconds": round(time.time() - started, 3),
                    "messages": history,
                    "trajectory": trajectory,
                }

            for call in calls:
                function = call["function"]
                arguments = function.get("arguments", "{}")
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                result = self.executor(function["name"], arguments)
                history.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": result,
                })
                record.setdefault("tool_calls", []).append({
                    "name": function["name"],
                    "arguments": arguments,
                    "result": result,
                })
            trajectory.append(record)

        return {
            "status": "max_steps_exceeded",
            "answer": "",
            "steps": self.config.max_steps,
            "elapsed_seconds": round(time.time() - started, 3),
            "messages": history,
            "trajectory": trajectory,
        }


if __name__ == "__main__":
    assert RuntimeConfig().max_steps == 8
    print("UNIFIED_AGENT_RUNTIME=OK")
