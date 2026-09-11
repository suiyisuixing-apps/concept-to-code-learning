import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import App from "./App.jsx";

let calls, saved, revision;
const record = { document_id: "reading", file_name: "划选示例.md", source_type: "MARKDOWN", unit_count: 2, revision: 1, original_sha256: "a".repeat(64) };
const units = [1, 2].map((i) => ({ unit_id: `unit-${i}`, unit_type: "section", index: i, heading_path: [`章节 ${i}`],
  extraction_status: "READY", preview: { kind: "learning_view", limitations: [] }, blocks: [
    { block_id: `first-${i}`, kind: "paragraph", text: "A😀保留零值" },
    { block_id: `second-${i}`, kind: "paragraph", text: "第二段文字" },
  ] }));
beforeEach(() => {
  calls = []; saved = []; revision = 0;
  Element.prototype.scrollIntoView = vi.fn();
  vi.stubGlobal("confirm", vi.fn(() => true));
  vi.stubGlobal("fetch", vi.fn(async (url, options = {}) => {
    calls.push([url, options]); let value;
    const body = options.body ? JSON.parse(options.body) : {};
    if (url.endsWith("/capabilities")) value = { tutor: { available: false } };
    else if (url.endsWith("/sessions")) value = { session_id: "reading-session", context_revision: 0 };
    else if (url.endsWith("/documents")) value = { documents: [record] };
    else if (url.endsWith("/units")) value = { units };
    else if (url.endsWith("/context")) value = { session_id: "reading-session", context_revision: ++revision };
    else if (url.endsWith("/explanations/stream")) value = { status: "COMPLETE", explanation: null, sources: [] };
    else if (url.includes("/annotations") && options.method === "POST") {
      value = { annotation_id: body.annotation_id, revision: 1, comment: body.comment,
        anchor: { document_id: record.document_id, document_revision: 1, original_sha256: record.original_sha256,
          file_name: record.file_name, unit_id: body.unit_id, unit_locator: { index: 1 },
          selected_text: body.selected_text, selected_text_hash: body.selected_text_hash, selection_locator: body.selection_locator } };
      saved.push(value);
    } else if (url.includes("/annotations/") && options.method === "PATCH") {
      const old = saved.find((a) => url.endsWith(a.annotation_id));
      value = { ...old, revision: old.revision + 1, comment: body.comment };
      saved = saved.map((a) => a === old ? value : a);
    } else if (url.includes("/annotations/") && options.method === "DELETE") {
      saved = saved.filter((a) => !url.endsWith(a.annotation_id)); value = {};
    } else if (url.includes("/annotations")) {
      const unit = new URL(url, "http://local").searchParams.get("unit_id");
      const annotations = saved.filter((a) => a.anchor.unit_id === unit);
      value = { annotations, total: annotations.length };
    } else if (url.includes("/notes")) value = { notes: [], total: 0 };
    else if (url.endsWith("/local-handles")) value = [];
    else value = {};
    return { ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => value };
  }));
});

function drag(first, start, last, end) {
  fireEvent.mouseDown(first, { button: 0 });
  const range = document.createRange(); range.setStart(first.firstChild, start); range.setEnd(last.firstChild, end);
  const selected = window.getSelection(); selected.removeAllRanges(); selected.addRange(range);
  fireEvent.mouseUp(last, { button: 0 });
}
async function chooseWhole(user, n = 1) {
  await user.click(await screen.findByRole("button", { name: `选择整段 ${n}` }));
  await screen.findByRole("button", { name: "清除引用" });
}

test("dragging cross-paragraph text fills an editable question while preserving exact source offsets", async () => {
  const user = userEvent.setup(); render(<App />);
  const first = await screen.findByText("A😀保留零值"), second = screen.getByText("第二段文字");
  drag(first, 1, second, 2);
  const input = screen.getByLabelText("学习问题");
  await waitFor(() => expect(input).toHaveValue("请解释这段原文：\n😀保留零值\n第二"));
  const original = JSON.parse(calls.filter(([url]) => url.endsWith("/context")).at(-1)[1].body);
  expect(original.selected_text).toBe("😀保留零值\n第二");
  expect(original.selection_locator.spans).toEqual([{ block_id: "first-1", start: 1, end: 6 }, { block_id: "second-1", start: 0, end: 2 }]);
  await user.clear(input); await user.type(input, "这段中的零值为什么不能丢弃？");
  await user.click(screen.getByRole("button", { name: "发送" }));
  await waitFor(() => expect(calls.some(([url]) => url.endsWith("/explanations/stream"))).toBe(true));
  expect(JSON.parse(calls.find(([url]) => url.endsWith("/explanations/stream"))[1].body).question).toBe("这段中的零值为什么不能丢弃？");
  expect(JSON.parse(calls.filter(([url]) => url.endsWith("/context")).at(-1)[1].body).selected_text).toBe(original.selected_text);
});

test("a new selection never overwrites a custom question and duplicate gestures do not reset context", async () => {
  const user = userEvent.setup(); render(<App />);
  await chooseWhole(user);
  const input = screen.getByLabelText("学习问题"); await user.clear(input); await user.type(input, "保留我正在写的问题");
  const before = calls.filter(([url]) => url.endsWith("/context")).length;
  await user.click(screen.getByRole("button", { name: "选择整段 1" }));
  expect(calls.filter(([url]) => url.endsWith("/context"))).toHaveLength(before);
  await user.click(screen.getByRole("button", { name: "选择整段 2" }));
  await waitFor(() => expect(calls.filter(([url]) => url.endsWith("/context"))).toHaveLength(before + 1));
  expect(input).toHaveValue("保留我正在写的问题");
  await user.click(screen.getByRole("button", { name: "带入问题" }));
  expect(input).toHaveValue("请解释这段原文：\n第二段文字");
  await user.click(screen.getByRole("button", { name: "清除引用" }));
  await waitFor(() => expect(input).toHaveValue(""));
});

test("DOM selection changes and clicks outside the reader never shorten a captured quote", async () => {
  const user = userEvent.setup(); render(<App />);
  const first = await screen.findByText("A😀保留零值"), second = screen.getByText("第二段文字");
  drag(first, 1, second, 2);
  const input = screen.getByLabelText("学习问题");
  await waitFor(() => expect(input).toHaveValue("请解释这段原文：\n😀保留零值\n第二"));
  const before = calls.filter(([url]) => url.endsWith("/context")).length;
  const marked = screen.getByText("😀保留零值");
  const range = document.createRange(); range.selectNodeContents(marked);
  const selected = window.getSelection(); selected.removeAllRanges(); selected.addRange(range);
  fireEvent(document, new Event("selectionchange"));
  await act(() => new Promise((resolve) => setTimeout(resolve, 220)));
  await user.click(screen.getByRole("button", { name: "写批注" }));
  expect(calls.filter(([url]) => url.endsWith("/context"))).toHaveLength(before);
  expect(within(screen.getByLabelText("文档批注")).getByText("😀保留零值 第二")).toBeVisible();
  expect(input).toHaveValue("请解释这段原文：\n😀保留零值\n第二");
});

test("annotations save without AI, survive reopening, and edit only personal commentary", async () => {
  const user = userEvent.setup(); const view = render(<App />);
  await chooseWhole(user); await user.click(screen.getByRole("button", { name: "写批注" }));
  await user.type(screen.getByLabelText("批注内容"), "我的改写：零值仍有意义 😀");
  await user.dblClick(screen.getByRole("button", { name: "保存批注" }));
  await screen.findByText(/批注已保存/);
  expect(saved).toHaveLength(1);
  expect(calls.filter(([url, options]) => url.includes("/annotations") && options.method === "POST")).toHaveLength(1);
  expect(calls.some(([url]) => url.endsWith("/explanations/stream"))).toBe(false);
  const anchor = saved[0].anchor;
  view.unmount(); render(<App />);
  await waitFor(() => expect(screen.getByRole("button", { name: "批注 1" })).toBeVisible());
  await user.click(screen.getByRole("button", { name: "批注 1" }));
  await user.click(screen.getByRole("button", { name: "编辑批注" }));
  await user.clear(screen.getByLabelText("批注内容")); await user.type(screen.getByLabelText("批注内容"), "修订后的个人理解");
  await user.click(screen.getByRole("button", { name: "保存批注" }));
  await screen.findByText("修订后的个人理解");
  expect(saved[0].revision).toBe(2); expect(saved[0].anchor).toEqual(anchor);
  await user.click(screen.getByRole("button", { name: "回到原文" }));
  await user.click(screen.getByRole("button", { name: "对话" }));
  await screen.findByRole("button", { name: "清除引用" });
  expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
});

test("navigation keeps an unfinished annotation tied to its original quote", async () => {
  const user = userEvent.setup(); render(<App />); await chooseWhole(user);
  await user.click(screen.getByRole("button", { name: "写批注" }));
  await user.type(screen.getByLabelText("批注内容"), "尚未保存的想法");
  await user.click(screen.getByRole("button", { name: "下一单元" }));
  await waitFor(() => expect(screen.getByLabelText("当前页或章节")).toHaveValue("unit-2"));
  await chooseWhole(user, 2); await user.click(screen.getByRole("button", { name: "写批注" }));
  expect(screen.getByLabelText("批注内容")).toHaveValue("尚未保存的想法");
  expect(screen.getByText(/当前批注还有未保存的内容/)).toBeVisible();
  await user.click(screen.getByRole("button", { name: "保存批注" }));
  await screen.findByText(/批注已保存/);
  expect(saved[0].anchor.unit_id).toBe("unit-1");
  expect(within(screen.getByLabelText("文档批注")).queryByText("尚未保存的想法")).not.toBeInTheDocument();
});

test("deleting an annotation requires confirmation and removes only that annotation", async () => {
  const user = userEvent.setup(); render(<App />); await chooseWhole(user);
  await user.click(screen.getByRole("button", { name: "写批注" }));
  await user.type(screen.getByLabelText("批注内容"), "临时批注"); await user.click(screen.getByRole("button", { name: "保存批注" }));
  await screen.findByText(/批注已保存/); await user.click(screen.getByRole("button", { name: "编辑批注" }));
  await user.click(screen.getByRole("button", { name: "删除批注" }));
  await screen.findByText("批注已删除。");
  expect(window.confirm).toHaveBeenCalled(); expect(saved).toHaveLength(0);
  expect(calls.some(([url, options]) => url.includes("/notes") && options.method === "DELETE")).toBe(false);
});
