import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import ModelPicker from "./ModelPicker.jsx";
import ErrorBoundary from "./ErrorBoundary.jsx";
import { SourceCard } from "./Conversation.jsx";
import { api, explainStream } from "./api.js";

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

test("a saved missing model cannot be sent or silently replaced", async () => {
  window.localStorage.setItem("c2c-model-choice", JSON.stringify({ id: "removed", base_url: "http://127.0.0.1:1234/v1" }));
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ models: [{ id: "available", name: "Available" }], default_model: "available" }), { headers: { "Content-Type": "application/json" } })));
  const change = vi.fn(), user = userEvent.setup();
  render(<ModelPicker change={change}/>);
  await screen.findByText("所选模型当前不可用，请重新选择。");
  expect(change.mock.calls.at(-1)[0]).toMatchObject({ id: "removed", ready: false });
  await user.selectOptions(screen.getByLabelText("选择模型"), "available");
  expect(change.mock.calls.at(-1)[0]).toMatchObject({ id: "available", ready: true });
  expect(screen.queryByText("所选模型当前不可用，请重新选择。")).not.toBeInTheDocument();
});

test("a broken result cannot crash the reader beside the conversation", () => {
  vi.spyOn(console, "error").mockImplementation(() => {});
  function Broken() { throw new Error("controlled render failure"); }
  const view = render(<><aside>仍可阅读的原文</aside><ErrorBoundary resetKey="old"><Broken/></ErrorBoundary></>);
  expect(screen.getByText("仍可阅读的原文")).toBeVisible();
  expect(screen.getByRole("alert")).toHaveTextContent("可以继续阅读或重新提问");
  view.rerender(<><aside>仍可阅读的原文</aside><ErrorBoundary resetKey="new"><p>新的有效回答</p></ErrorBoundary></>);
  expect(screen.getByText("新的有效回答")).toBeVisible();
});

test("fixture source is visibly and accessibly different from verified source", () => {
  const source = { mode: "FIXTURE", code_excerpt: "print('fixture')", file_path: "example.py",
    verification_status: "VERIFIED", provenance_kind: "SOURCE_EXACT", license_observation: { files: [] }, relevance: { reason: "Synthetic fixture" } };
  render(<SourceCard source={source}/>);
  expect(screen.getByText("演示来源 · Fixture")).toBeVisible();
  expect(screen.queryByLabelText("已核验原始代码")).not.toBeInTheDocument();
});

test("broken JSON is a recoverable product error", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("{broken", { headers: { "Content-Type": "application/json" } })));
  await expect(api("/sessions/recent")).rejects.toMatchObject({ code: "INVALID_RESPONSE", retryable: true });
});

test("invalid streamed result and malformed NDJSON are rejected before rendering", async () => {
  for (const body of ['{"type":"result","value":{"status":"COMPLETE"}}\n', '{broken}\n']) {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(body, { headers: { "Content-Type": "application/x-ndjson" } })));
    await expect(explainStream({}, null, vi.fn())).rejects.toMatchObject({ code: "INVALID_RESPONSE", retryable: true });
  }
});

test("reader cleanup cannot hide a structured stream failure", async () => {
  const reader = { read: vi.fn(async () => ({ value: new TextEncoder().encode('{"type":"error","value":{"code":"MODEL_OUTPUT_INVALID","user_message":"重试"}}\n'), done: false })), cancel: vi.fn(async () => { throw new Error("cleanup failure"); }), releaseLock: vi.fn() };
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, headers: new Headers({ "Content-Type": "application/x-ndjson" }), body: { getReader: () => reader } })));
  await expect(explainStream({}, null, vi.fn())).rejects.toMatchObject({ code: "MODEL_OUTPUT_INVALID" });
  expect(reader.releaseLock).toHaveBeenCalled();
});

test("browser deadline recovers from an endpoint that never answers", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("fetch", vi.fn((url, { signal }) => new Promise((resolve, reject) => signal.addEventListener("abort", () => reject(signal.reason)))));
  const expected = expect(explainStream({}, null, vi.fn())).rejects.toMatchObject({ code: "REQUEST_TIMEOUT", retryable: true });
  await vi.advanceTimersByTimeAsync(150000);
  await expected;
});

test("history reports skipped rows without altering the list contract", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("[]", { headers: { "Content-Type": "application/json", "X-C2C-Skipped-History": "2" } })));
  const history = await api("/sessions/s1/history");
  expect(history).toEqual([]);
  expect(history.skippedCount).toBe(2);
  await waitFor(() => expect(JSON.stringify(history)).toBe("[]"));
});
