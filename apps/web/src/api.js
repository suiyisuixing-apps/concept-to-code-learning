const BASE = "/api/learning/v1";

export class ApiError extends Error {
  constructor(payload, status) {
    super(payload?.user_message || payload?.detail || "请求未完成，请稍后重试。");
    this.code = payload?.code || `HTTP_${status}`;
    this.retryable = Boolean(payload?.retryable);
    this.neededAction = payload?.needed_action;
  }
}

function invalidResponse() {
  return new ApiError({ code: "INVALID_RESPONSE", user_message: "回答数据不完整，请重试。", retryable: true }, 502);
}
function parseLine(text) { try { return JSON.parse(text); } catch { throw invalidResponse(); } }
async function readJson(response) { try { return await response.json(); } catch { throw invalidResponse(); } }

export function checkedResult(value) {
  if (value?.status === "NEEDS_SOURCE_SELECTION" && Array.isArray(value.candidates)
      && value.candidates.every((item) => typeof item?.candidate_id === "string") && value.query_id) return value;
  const answer = value?.explanation;
  if (value?.status !== "COMPLETE" || !answer || typeof answer.question !== "string"
      || !answer.context_snapshot || !answer.explanation_id || !answer.provider_info || !answer.metrics
      || !Array.isArray(value.sources) || !Array.isArray(answer.answer_sections)
      || !answer.answer_sections.every((item) => typeof item?.title === "string" && typeof item?.text === "string")
      || !["example_blocks", "document_citations", "concept_code_links", "limitations"].every((key) => Array.isArray(answer[key]))) {
    throw invalidResponse();
  }
  return value;
}

export async function api(path, options = {}) {
  let response;
  try { response = await fetch(`${BASE}${path}`, options); }
  catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError({ code: "CONNECTION_LOST", user_message: "本地服务未连接。请启动应用后重试。", retryable: true }, 0);
  }
  if (response.status === 204) return null;
  const type = response.headers?.get?.("content-type") || "";
  const value = type.includes("json") ? await readJson(response) : await response.text();
  if (!response.ok) throw new ApiError(value, response.status);
  if (Array.isArray(value)) Object.defineProperty(value, "skippedCount", {
    value: Number(response.headers?.get?.("X-C2C-Skipped-History")) || 0,
  });
  return value;
}

export function json(method, body) {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

export async function explainStream(body, signal, progress) {
  const controller = new AbortController();
  const abort = () => controller.abort(signal.reason);
  if (signal?.aborted) abort();
  else signal?.addEventListener("abort", abort, { once: true });
  // Server timeout is 120 seconds. Also recover if a proxy or broken stream
  // leaves the browser waiting without receiving a terminal event.
  const deadline = setTimeout(() => controller.abort(new ApiError({ code: "REQUEST_TIMEOUT",
    user_message: "等待回答超时，请检查模型服务后重试。", retryable: true }, 504)), 150000);
  try { return await readExplanation(body, controller.signal, progress); }
  catch (error) {
    if (controller.signal.aborted) throw controller.signal.reason;
    throw error;
  } finally { clearTimeout(deadline); signal?.removeEventListener("abort", abort); }
}

async function readExplanation(body, signal, progress) {
  let response;
  try { response = await fetch(`${BASE}/explanations/stream`, { ...json("POST", body), signal }); }
  catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError({ code: "CONNECTION_LOST", user_message: "连接中断，请重试。", retryable: true }, 0);
  }
  if (response.headers.get("content-type")?.includes("json") && !response.headers.get("content-type")?.includes("ndjson")) {
    const value = await readJson(response);
    if (!response.ok) throw new ApiError(value, response.status);
    return checkedResult(value);
  }
  if (!response.ok || !response.body) throw new ApiError({ user_message: "连接中断，请重试。", retryable: true }, response.status);
  const reader = response.body.getReader(), decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      if (buffer.length > 4 * 1024 * 1024) throw invalidResponse();
      let newline;
      while ((newline = buffer.indexOf("\n")) !== -1) {
        const line = buffer.slice(0, newline); buffer = buffer.slice(newline + 1);
        if (!line.trim()) continue;
        const event = parseLine(line);
        if (!event || typeof event !== "object") throw invalidResponse();
        if (event.type === "progress") progress(event.stage);
        if (event.type === "preview") {
          if (!Array.isArray(event.sections) || !event.sections.every((item) => typeof item?.title === "string" && typeof item?.text === "string")) throw invalidResponse();
          progress(event);
        }
        if (event.type === "error") throw new ApiError(event.value, 502);
        if (event.type === "result") return checkedResult(event.value);
      }
      if (done) break;
    }
    throw new ApiError({ code: "CONNECTION_LOST", user_message: "回答途中连接中断，请重试。", retryable: true }, 0);
  } finally {
    try { await reader.cancel(); } catch { /* Preserve the original result or failure. */ }
    try { reader.releaseLock(); } catch { /* A failed stream may already be detached. */ }
  }
}

export function id(prefix = "request") { return `${prefix}-${crypto.randomUUID()}`; }

export async function hashText(text) {
  if (!text) return null;
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function utf16ToCodePoint(text, offset) { return Array.from(text.slice(0, offset)).length; }

export function assetUrl(documentId, assetId) {
  return `${BASE}/documents/${encodeURIComponent(documentId)}/assets/${encodeURIComponent(assetId)}`;
}
