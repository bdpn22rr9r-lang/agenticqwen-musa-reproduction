#!/usr/bin/env node
/** Run one BFCL Agentic task, including optional memory prerequisite sessions. */
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { pathToFileURL } from "node:url";
import readline from "node:readline";

function value(flag, fallback = undefined) {
  const index = process.argv.indexOf(flag);
  if (index < 0) return fallback;
  if (!process.argv[index + 1]) throw new Error(`missing ${flag}`);
  return process.argv[index + 1];
}

function safe(value) {
  try { return JSON.parse(JSON.stringify(value)); } catch { return { unserializable: String(value) }; }
}

function textForTurn(turn) {
  return (turn || []).map((message) => {
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

const maxStepsPerTurn = Number(input.maxStepsPerTurn ?? 8);
const maxStepsPerTask = Number(input.maxStepsPerTask ?? 256);
let totalCalls = 0;
let currentSession = -1;
let currentTurn = -1;
let turnCalls = 0;
const callsBySession = [];
const assistantResponses = [];
const events = [];
const broker = spawn("python3", [executor, "--serve"], { stdio: ["pipe", "pipe", "pipe"] });
const pending = new Map();
let sequence = 0;
let brokerError = "";
broker.stderr.on("data", (chunk) => { brokerError += chunk.toString(); });
readline.createInterface({ input: broker.stdout }).on("line", (line) => {
  try {
    const response = JSON.parse(line);
    const resolve = pending.get(response.request_id);
    if (resolve) { pending.delete(response.request_id); resolve(response); }
  } catch (error) {
    brokerError += `invalid broker response: ${error}\n`;
  }
});

function latestAssistantText(start) {
  for (let index = events.length - 1; index >= start; index -= 1) {
    const event = events[index];
    if (event?.type !== "message_end" || event?.message?.role !== "assistant") continue;
    const content = event.message.content;
    if (typeof content === "string") return content;
    if (Array.isArray(content)) {
      return content.map((block) => typeof block === "string" ? block : block?.text || "").join("");
    }
    return content == null ? "" : JSON.stringify(content);
  }
  return "";
}

function requestBroker(request) {
  return new Promise((resolve, reject) => {
    pending.set(request.request_id, (response) => {
      if (response.error) reject(new Error(`BFCL_EXECUTOR_FAILED: ${response.error}`));
      else resolve(response);
    });
    broker.stdin.write(JSON.stringify(request) + "\n", (error) => error && reject(error));
  });
}

function execute(name, arguments_) {
  const session = input.sessions[currentSession];
  const sessionCalls = callsBySession[currentSession];
  if (turnCalls >= maxStepsPerTurn) throw new Error("MAX_TURN_STEPS_EXCEEDED");
  if (sessionCalls.length >= Number(input.maxStepsPerSession ?? 32)) throw new Error("MAX_SESSION_STEPS_EXCEEDED");
  if (totalCalls >= maxStepsPerTask) throw new Error("MAX_TASK_STEPS_EXCEEDED");
  const request_id = String(++sequence);
  return requestBroker({
    request_id,
    name,
    arguments: arguments_,
    initial_config: session.initial_config,
    involved_classes: session.involved_classes,
    model: input.model,
    task_id: session.task_id,
    long_context: Boolean(input.category?.includes("long_context")),
  }).then((response) => {
    totalCalls += 1;
    turnCalls += 1;
    sessionCalls.push({ name, arguments: arguments_, call_text: response.call_text, result: response.content });
    return response.content;
  });
}

const tools = input.tools.map((tool) => defineTool({
  name: tool.function.name,
  label: tool.function.name,
  description: tool.function.description || "",
  promptSnippet: `${tool.function.name}: ${tool.function.description || "BFCL Agentic task tool"}`,
  promptGuidelines: [`Use ${tool.function.name} only when the task requires it; call the tool instead of describing the call.`],
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
  systemPromptOverride: () => "You are an evaluation agent. Use only the provided task tools when needed. Do not describe tools; call them. For your final answer to the user, you must respond in this format: {'answer': A short and precise answer to the question, 'context': A brief explanation of how you arrived at this answer or why it is correct}. If you do not know the answer, respond with {'answer': 'I do not know', 'context': 'I do not know'}. If you think the question cannot be properly answered, respond with {'answer': 'I cannot answer this question', 'context': A short reason explaining why this question cannot be answered}.",
});
await loader.reload();
const flush = async (session) => {
  if (!session.flush) return;
  await requestBroker({ request_id: String(++sequence), op: "flush", task_id: session.task_id });
};

for (currentSession = 0; currentSession < input.sessions.length; currentSession += 1) {
  const sessionInput = input.sessions[currentSession];
  callsBySession.push([]);
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
  for (currentTurn = 0; currentTurn < sessionInput.question.length; currentTurn += 1) {
    const before = events.length;
    turnCalls = 0;
    await session.prompt(textForTurn(sessionInput.question[currentTurn]));
    assistantResponses.push({ session: currentSession, turn: currentTurn, text: latestAssistantText(before) });
  }
  session.dispose();
  await flush(sessionInput);
}
broker.stdin.end();
broker.kill();
if (brokerError) events.push({ type: "bfcl_executor_stderr", text: brokerError });
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify({
  id: input.id,
  category: input.category,
  events,
  calls_by_session: callsBySession,
  assistant_responses: assistantResponses,
  total_calls: totalCalls,
}, null, 2));
