import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import App from "./App.jsx";
import { ApiError, api, assetUrl, hashText, json, utf16ToCodePoint } from "./api.js";

let calls;
beforeEach(() => {
  calls = [];
  vi.stubGlobal("fetch", vi.fn(async (url, options = {}) => {
    calls.push([url, options]);
    let body = {};
    if (url.endsWith("/capabilities")) body = { integrated_product: "UNAVAILABLE", tutor: { available: false, needed_action: "配置本地模型" } };
    else if (url.endsWith("/sessions")) body = { session_id: "session-1", context_revision: 0, status: "EMPTY" };
    else if (url.endsWith("/documents")) body = { documents: [] };
    else if (url.includes("/notes")) body = { notes: [] };
    return { ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body };
  }));
});

test("shows a usable workspace and truthful unavailable model state", async () => {
  render(<App />);
  expect(await screen.findByText("模型尚未配置")).toBeVisible();
  expect(screen.getByText("配置本地模型")).toBeVisible();
  expect(screen.getByText("导入学习材料")).toBeVisible();
  expect(screen.getByText("暂无代码来源")).toBeVisible();
  expect(screen.getByRole("button", { name: "开始讲解" })).toBeDisabled();
});

test("authorization and all four levels are operable", async () => {
  const user = userEvent.setup(); render(<App />); await screen.findByText("模型尚未配置");
  await user.selectOptions(screen.getByLabelText("来源模式"), "public_search");
  expect(screen.getByText("确认发送搜索词")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Engineering" }));
  expect(screen.getByRole("button", { name: "Engineering" })).toHaveAttribute("aria-pressed", "true");
  await user.click(screen.getByRole("button", { name: "高级选项" }));
  expect(screen.getByText("比较两个仓库")).toBeVisible();
});

test("notes search is debounced", async () => {
  const user = userEvent.setup(); render(<App />);
  await user.click(await screen.findByRole("button", { name: "笔记 0" }));
  await user.type(screen.getByLabelText("搜索笔记"), "中文");
  await waitFor(() => expect(calls.some(([url]) => url.includes("notes?q=%E4%B8%AD%E6%96%87"))).toBe(true));
});

test("UTF-16 offsets convert to Python Unicode code points", () => {
  expect(utf16ToCodePoint("A😀中文", 3)).toBe(2);
  expect(utf16ToCodePoint("😀x", 2)).toBe(1);
});

test("structured backend errors preserve retry guidance", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: false,
    status: 503,
    headers: { get: () => "application/json" },
    json: async () => ({ code: "MODEL_UNAVAILABLE", user_message: "模型暂不可用", retryable: true,
      needed_action: "检查本地模型" }),
  })));
  await expect(api("/capabilities")).rejects.toMatchObject({
    code: "MODEL_UNAVAILABLE", retryable: true, neededAction: "检查本地模型",
  });
  expect(new ApiError({}, 500).code).toBe("HTTP_500");
});

test("JSON requests and asset URLs preserve the public API boundary", () => {
  expect(json("PATCH", { title: "中文" })).toEqual({
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: '{"title":"中文"}',
  });
  expect(assetUrl("doc-one", "image one")).toBe(
    "/api/learning/v1/documents/doc-one/assets/image%20one",
  );
});

test("SHA-256 hashes UTF-8 selection text", async () => {
  await expect(hashText("😀")).resolves.toMatch(/^[a-f0-9]{64}$/);
  await expect(hashText("")).resolves.toBeNull();
});

test("blank questions remain disabled without losing source settings", async () => {
  const user = userEvent.setup(); render(<App />); await screen.findByText("模型尚未配置");
  await user.type(screen.getByLabelText("公开仓库"), "owner/repo");
  expect(screen.getByRole("button", { name: "开始讲解" })).toBeDisabled();
  expect(screen.getByLabelText("公开仓库")).toHaveValue("owner/repo");
});

test("search selects a complete emoji block with code-point offsets", async () => {
  const record = { document_id: "doc-abc", file_name: "emoji.md", source_type: "MARKDOWN", unit_count: 1, revision: 1 };
  const unit = { unit_id: "section-1", unit_type: "section", index: 1, heading_path: ["标题"],
    extraction_status: "READY", preview: { kind: "learning_view", limitations: [] },
    blocks: [{ block_id: "section-1-block-1", kind: "paragraph", text: "A😀中文", table_rows: [], image_asset_id: null }] };
  const requests = [];
  vi.stubGlobal("fetch", vi.fn(async (url, options = {}) => {
    requests.push([url, options]); let value;
    if (url.endsWith("/capabilities")) value = { integrated_product: "UNAVAILABLE", tutor: { available: false } };
    else if (url.endsWith("/sessions")) value = { session_id: "session-1", context_revision: 0, status: "EMPTY" };
    else if (url.endsWith("/documents")) value = { documents: [record] };
    else if (url.endsWith("/units")) value = { units: [unit] };
    else if (url.includes("/context")) value = { session_id: "session-1", context_revision: requests.filter(([x]) => x.includes("/context")).length, status: "READY" };
    else if (url.includes("/annotations")) value = { annotations: [], total: 0 };
    else if (url.includes("/notes")) value = { notes: [] };
    return { ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => value };
  }));
  const user = userEvent.setup(); render(<App />);
  await user.type(await screen.findByLabelText("搜索当前单元"), "😀");
  await user.click(screen.getByRole("button", { name: "选择：A😀中文" }));
  await waitFor(() => expect(requests.filter(([url]) => url.includes("/context"))).toHaveLength(2));
  const selectionBody = JSON.parse(requests.filter(([url]) => url.includes("/context"))[1][1].body);
  expect(selectionBody.selection_locator.spans[0]).toEqual({
    block_id: "section-1-block-1", start: 0, end: 4,
  });
  expect(selectionBody.selected_text).toBe("A😀中文");
});


function deferred() { let resolve; const promise = new Promise((done) => { resolve = done; }); return { promise, resolve }; }
function readyWorkspace(hook = () => undefined) {
  const record = { document_id: "doc-live", file_name: "学习.md", source_type: "MARKDOWN", unit_count: 3, revision: 1 };
  const units = [1, 2, 3].map((i) => ({ unit_id: `section-${i}`, index: i, unit_type: "section", heading_path: [`章节${i}`],
    extraction_status: "READY", preview: { kind: "learning_view", limitations: [] },
    blocks: [{ block_id: `block-${i}`, kind: "paragraph", text: `单元内容${i}` }] }));
  let revision = 0;
  const requests = [];
  vi.stubGlobal("fetch", vi.fn(async (url, options = {}) => {
    requests.push([url, options]); let value = await hook(url, options, requests);
    if (value === undefined) {
      if (url.endsWith("/capabilities")) value = { tutor: { available: true } };
      else if (url.endsWith("/sessions")) value = { session_id: "s1", context_revision: 0 };
      else if (url.endsWith("/documents")) value = { documents: [record] };
      else if (url.endsWith("/units")) value = { units };
      else if (url.endsWith("/context")) value = { session_id: "s1", context_revision: ++revision };
      else if (url.endsWith("/local-handles")) value = { handles: [] };
      else if (url.includes("/annotations")) value = { annotations: [], total: 0 };
    else if (url.includes("/notes")) value = { notes: [], total: 0 };
      else value = {};
    }
    return { ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => value };
  }));
  return requests;
}
function answer(question = "最初的问题") {
  return { status: "COMPLETE", sources: [], explanation: {
    explanation_id: "explanation-1", question, status: "NO_VERIFIED_CODE", level: "Beginner",
    answer_sections: [{ title: "解释结果", text: "只属于当前请求的回答" }], document_citations: [],
    concept_code_links: [], example_blocks: [], limitations: [], provider_info: { model_id: "local-model" },
    metrics: { latency_ms: 100, token_source: "PROVIDER_USAGE", input_tokens: 10, output_tokens: 20 },
  } };
}

test("navigation cancels an in-flight answer and late results cannot replace the new unit", async () => {
  const late = deferred();
  const requests = readyWorkspace((url) => url.endsWith("/explanations") ? late.promise : undefined);
  const user = userEvent.setup(); render(<App />);
  await user.type(await screen.findByLabelText("学习问题"), "最初的问题");
  await waitFor(() => expect(screen.getByRole("button", { name: "开始讲解" })).toBeEnabled());
  await user.click(screen.getByRole("button", { name: "开始讲解" }));
  await screen.findByRole("button", { name: "取消" });
  await user.click(screen.getByRole("button", { name: "下一单元" }));
  await waitFor(() => expect(screen.getByLabelText("当前页或章节")).toHaveValue("section-2"));
  await act(async () => late.resolve(answer()));
  expect(screen.queryByText("只属于当前请求的回答")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "开始讲解" })).toBeEnabled();
  expect(requests.some(([url, options]) => url.includes("/requests/") && options.method === "DELETE")).toBe(true);
  expect(requests.find(([url]) => url.endsWith("/explanations"))[1].signal.aborted).toBe(true);
});

test("rapid context changes serialize revisions and retain the last selected unit", async () => {
  const second = deferred(); let count = 0;
  const requests = readyWorkspace((url) => {
    if (url.endsWith("/context")) { count++; if (count === 2) return second.promise; if (count === 3) return { session_id: "s1", context_revision: 3 }; }
  });
  const user = userEvent.setup(); render(<App />);
  await screen.findByText("单元内容1");
  await user.selectOptions(screen.getByLabelText("当前页或章节"), "section-2");
  await waitFor(() => expect(count).toBe(2));
  await user.selectOptions(screen.getByLabelText("当前页或章节"), "section-3");
  await act(async () => second.resolve({ session_id: "s1", context_revision: 2 }));
  await screen.findByText("单元内容3");
  const contexts = requests.filter(([url]) => url.endsWith("/context"));
  expect(JSON.parse(contexts[2][1].body)).toMatchObject({ unit_id: "section-3", expected_context_revision: 2 });
});

test("saving retains the answered question and duplicate clicks create one note", async () => {
  const saved = deferred();
  const requests = readyWorkspace((url, options) => {
    if (url.endsWith("/explanations")) return answer();
    if (url.endsWith("/notes") && options.method === "POST") return saved.promise;
  });
  const user = userEvent.setup(); render(<App />);
  await user.type(await screen.findByLabelText("学习问题"), "最初的问题");
  await waitFor(() => expect(screen.getByRole("button", { name: "开始讲解" })).toBeEnabled());
  await user.click(screen.getByRole("button", { name: "开始讲解" }));
  await screen.findByText("只属于当前请求的回答");
  await user.clear(screen.getByLabelText("学习问题"));
  await user.type(screen.getByLabelText("学习问题"), "下一条尚未回答的问题");
  await user.dblClick(screen.getByRole("button", { name: "保存为笔记" }));
  const saves = requests.filter(([url, options]) => url.endsWith("/notes") && options.method === "POST");
  expect(saves).toHaveLength(1);
  expect(JSON.parse(saves[0][1].body).title).toBe("最初的问题");
  await act(async () => saved.resolve({ note_id: "note-1", title: "最初的问题", revision: 1 }));
  await screen.findByText("笔记已保存。后续修改可在右侧「笔记」中编辑。");
});
