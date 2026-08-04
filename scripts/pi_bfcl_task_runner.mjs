#!/usr/bin/env node
/** Run one BFCL task through Pi with only task-provided custom tools enabled. */
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { pathToFileURL } from "node:url";
import readline from "node:readline";

function value(flag) {
  const index = process.argv.indexOf(flag);
  if (index < 0 || !process.argv[index + 1]) throw new Error(`missing ${flag}`);
  return process.argv[index + 1];
}

function safe(value) {
  try {
    return JSON.parse(JSON.stringify(value));
  } catch {
    return { unserializable: String(value) };
  }
}

function textForTurn(turn) {
  return turn.map((message) => {
    const content = message.content;
    if (typeof content === "string") return content;
    return JSON.stringify(content ?? "");
  }).join("\n");
}

function esmEntry(packageDirectory) {
  const descriptor = JSON.parse(fs.readFileSync(path.join(packageDirectory, "package.json"), "utf8"));
  const exported = descriptor.exports?.["."];
  const entry = typeof exported === "string" ? exported : exported?.import ?? descriptor.main;
  if (typeof entry !== "string") throw new Error(`ESM_ENTRY_NOT_FOUND: ${packageDirectory}`);
  return pathToFileURL(path.resolve(packageDirectory, entry)).href;
}

const inputPath = value("--input");
const outputPath = value("--output");
const input = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const app = process.env.PI_APP;
const executor = process.env.PI_EXECUTOR_PY;
if (!app || !executor) throw new Error("PI_APP and PI_EXECUTOR_PY are required");

const piPackage = path.join(app, "node_modules", "@earendil-works", "pi-coding-agent");
const pi = await import(esmEntry(piPackage));
const typebox = await import(esmEntry(path.join(piPackage, "node_modules", "typebox")));
const { createAgentSession, DefaultResourceLoader, ModelRuntime, SessionManager, SettingsManager, defineTool } = pi;
const { Type } = typebox;

let turnIndex = 0;
let callCount = 0;
const callsByTurn = input.entry.question.map(() => []);
const events = [];
const broker = spawn("python3", [executor, "--serve"], { stdio: ["pipe", "pipe", "pipe"] });
const pending = new Map();
let sequence = 0;
let brokerError = "";
broker.stderr.on("data", (chunk) => { brokerError += chunk.toString(); });
readline.createInterface({ input: broker.stdout }).on("line", (line) => {
  const response = JSON.parse(line);
  const resolve = pending.get(response.request_id);
  if (resolve) { pending.delete(response.request_id); resolve(response); }
});

function execute(name, arguments_) {
  if (callCount >= input.maxSteps) throw new Error("MAX_STEPS_EXCEEDED");
  const request_id = String(++sequence);
  const request = {
    request_id,
    name,
    arguments: arguments_,
    initial_config: input.entry.initial_config,
    involved_classes: input.entry.involved_classes,
    model: input.model,
    task_id: input.entry.id,
    long_context: input.category.includes("long_context"),
  };
  return new Promise((resolve, reject) => {
    pending.set(request_id, (response) => {
      if (response.error) return reject(new Error(`BFCL_EXECUTOR_FAILED: ${response.error}`));
      callCount += 1;
      callsByTurn[turnIndex].push({ name, arguments: arguments_, call_text: response.call_text, result: response.content });
      resolve(response.content);
    });
    broker.stdin.write(JSON.stringify(request) + "\n", (error) => error && reject(error));
  });
}

const tools = input.tools.map((tool) => defineTool({
  name: tool.function.name,
  label: tool.function.name,
  description: tool.function.description || "",
  promptSnippet: `${tool.function.name}: ${tool.function.description || "BFCL task tool"}`,
  promptGuidelines: [`Use ${tool.function.name} only when the BFCL task requires it; call the tool instead of describing the call.`],
  parameters: Type.Unsafe(tool.function.parameters),
  execute: async (_toolCallId, arguments_) => ({
    content: [{ type: "text", text: await execute(tool.function.name, arguments_) }], details: {},
  }),
}));

const modelRuntime = await ModelRuntime.create({ modelsPath: process.env.PI_MODELS, authPath: process.env.PI_AUTH });
const model = modelRuntime.getModel(input.provider, input.model);
if (!model) throw new Error(`PI_MODEL_NOT_FOUND: ${input.provider}/${input.model}`);
const settingsManager = SettingsManager.inMemory({ compaction: { enabled: false }, retry: { enabled: false } });
const loader = new DefaultResourceLoader({
  cwd: process.env.PI_CWD || "/tmp",
  agentDir: process.env.PI_AGENT_DIR,
  settingsManager,
  systemPromptOverride: () => "You are an evaluation agent. Use only the provided task tools when needed. Do not describe tools; call them.",
});
await loader.reload();
const { session } = await createAgentSession({
  model,
  modelRuntime,
  thinkingLevel: "off",
  customTools: tools,
  tools: tools.map((tool) => tool.name),
  resourceLoader: loader,
  sessionManager: SessionManager.inMemory(),
  settingsManager,
});
session.subscribe((event) => events.push(safe(event)));

for (turnIndex = 0; turnIndex < input.entry.question.length; turnIndex += 1) {
  await session.prompt(textForTurn(input.entry.question[turnIndex]));
}
session.dispose();
broker.stdin.end();
broker.kill();
if (brokerError) events.push({ type: "bfcl_executor_stderr", text: brokerError });
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify({ id: input.entry.id, events, calls_by_turn: callsByTurn }, null, 2));
