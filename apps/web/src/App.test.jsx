import { render, screen, waitFor } from "@testing-library/react";
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
