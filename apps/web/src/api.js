const BASE = "/api/learning/v1";

export class ApiError extends Error {
  constructor(payload, status) {
    super(payload?.user_message || payload?.detail || "请求未完成，请稍后重试。");
    this.code = payload?.code || `HTTP_${status}`;
    this.retryable = Boolean(payload?.retryable);
    this.neededAction = payload?.needed_action;
  }
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
  const value = type.includes("json") ? await response.json() : await response.text();
  if (!response.ok) throw new ApiError(value, response.status);
  return value;
}

export function json(method, body) {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
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
