import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import App from "./App.jsx";
import { utf16ToCodePoint } from "./api.js";

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
