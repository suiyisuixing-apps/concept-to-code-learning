import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import App from "./App.jsx";
import RepositoryPane from "./RepositoryPane.jsx";

const repo = { repository_id: "repo-test", repository: "fixture/code", commit_sha: "a".repeat(40), complete_tree: true };
const location = { ...repo, file_path: "src/main.py", line_start: 1, line_end: 3 };
const record = { document_id: "code-test", source_type: "CODE", revision: 1, file_name: "main.py", code_location: location, code_license: { files: [{ identifier: "MIT" }] } };
const unit = { unit_id: "code-unit", index: 1, blocks: [{ block_id: "code-block", text: "# 中文 😀\ndef square(x):\n    return x * x", code_location: location }] };
const response = (body) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
const entry = { path: "src/main.py", kind: "file", sha: "b".repeat(40), size: 40 };
const folder = { path: "src", kind: "folder", sha: "c".repeat(40) };
function props(extra = {}) { return { record, unit, units: [unit], select: vi.fn(), navigate: vi.fn(), openFile: vi.fn(), annotate: vi.fn(), repositories: [repo], setRepositories: vi.fn(), resetError: vi.fn(), ...extra }; }

beforeEach(() => {
  window.sessionStorage.clear();
  vi.stubGlobal("fetch", vi.fn(async (url) => response({ entries: url.includes("directory=src") ? [entry] : [folder], total: 1, complete_tree: true })));
});

test("folders expand lazily and filenames open the correct repository path", async () => {
  const user = userEvent.setup(), values = props({ record: null, unit: null }); render(<RepositoryPane {...values}/>);
  const src = await screen.findByRole("button", { name: "src" });
  expect(src).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByRole("button", { name: "main.py" })).not.toBeInTheDocument();
  await user.click(src);
  await user.click(await screen.findByRole("button", { name: "main.py" }));
  expect(values.openFile).toHaveBeenCalledWith(repo, "src/main.py");
  await user.click(src);
  expect(screen.queryByRole("button", { name: "main.py" })).not.toBeInTheDocument();
});

test("line and shift selection preserve Unicode code point offsets and exact line breaks", async () => {
  const user = userEvent.setup(), values = props(); render(<RepositoryPane {...values}/>);
  await user.click(screen.getByRole("button", { name: "选择第 1 行" }));
  expect(values.select).toHaveBeenLastCalledWith({ text: "# 中文 😀", spans: [{ block_id: "code-block", start: 0, end: 6 }] });
  await user.keyboard("{Shift>}");
  await user.click(screen.getByRole("button", { name: "选择第 3 行" }));
  await user.keyboard("{/Shift}");
  expect(values.select.mock.calls.at(-1)[0].text).toBe(unit.blocks[0].text);
  expect(values.select.mock.calls.at(-1)[0].spans[0].end).toBe(Array.from(unit.blocks[0].text).length);
  expect(document.querySelector(".code-content code").textContent).toBe(unit.blocks[0].text);
});

test("native mouse selection in highlighted code records server-compatible text", () => {
  const values = props(); render(<RepositoryPane {...values}/>);
  const line = document.querySelector(".code-line .syntax-comment");
  const range = document.createRange(); range.setStart(line.firstChild, 2); range.setEnd(line.firstChild, 7);
  const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
  fireEvent.mouseUp(screen.getByLabelText("源码阅读区"));
  expect(values.select).toHaveBeenCalledWith({ text: "中文 😀", spans: [{ block_id: "code-block", start: 2, end: 6 }] });
  selection.removeAllRanges();
});

test("a late file search cannot overwrite a newer query", async () => {
  let resolveOld;
  vi.stubGlobal("fetch", vi.fn(async (url) => {
    if (url.includes("q=old")) return new Promise((resolve) => { resolveOld = () => resolve(response({ entries: [{ ...entry, path: "old.py" }], total: 1 })); });
    return response({ entries: url.includes("q=new") ? [{ ...entry, path: "new.py" }] : [folder], total: 1 });
  }));
  const user = userEvent.setup(); render(<RepositoryPane {...props()}/>);
  await user.type(screen.getByLabelText("查找仓库文件"), "old");
  await waitFor(() => expect(resolveOld).toBeTypeOf("function"));
  await user.clear(screen.getByLabelText("查找仓库文件")); await user.type(screen.getByLabelText("查找仓库文件"), "new");
  expect(await screen.findByRole("button", { name: "new.py" })).toBeVisible();
  await act(async () => resolveOld());
  expect(screen.queryByRole("button", { name: "old.py" })).not.toBeInTheDocument();
});

test("repository read errors preserve the current file and provide retry and fixed source link", async () => {
  const retry = vi.fn(), values = props({ error: { message: "未确认展示许可", retry, url: "https://github.com/fixture/code/blob/" + repo.commit_sha + "/other.py" } });
  const user = userEvent.setup(); render(<RepositoryPane {...values}/>);
  const error = screen.getByRole("alert"); expect(error).toHaveTextContent("未确认展示许可");
  expect(within(error).getByRole("link", { name: "在 GitHub 查看" })).toHaveAttribute("href", values.error.url);
  await user.click(within(error).getByRole("button", { name: "重试" })); expect(retry).toHaveBeenCalledOnce();
  expect(screen.getByLabelText("源码阅读区")).toHaveTextContent("square");
});

test("the workspace sends code questions only for its repository, restores code after mode changes and keeps failures editable", async () => {
  let sent, revision = 0;
  window.sessionStorage.setItem("c2c-workspace", JSON.stringify({ question: "之前选区的自动问题", autoQuestion: "之前选区的自动问题" }));
  vi.stubGlobal("fetch", vi.fn(async (url, options = {}) => {
    if (url.endsWith("/capabilities")) return response({ tutor: { available: true } });
    if (url.endsWith("/models")) return response({ models: [{ id: "fixture-model", name: "Fixture model" }] });
    if (url.endsWith("/repositories")) return response([repo]);
    if (url.includes("/tree?")) return response({ entries: [entry], total: 1 });
    if (url.includes("/files?")) return response({ document: record, units: [unit] });
    if (url.endsWith("/documents")) return response({ documents: [] });
    if (url.includes("/notes")) return response({ notes: [] });
    if (url.endsWith("/context")) return response({ session_id: "test-session", context_revision: ++revision });
    if (url.includes("/sessions")) return response({ session_id: "test-session", context_revision: 0 });
    if (url.includes("/explanations")) {
      sent = JSON.parse(options.body);
      return { ok: false, status: 503, headers: { get: () => "application/json" }, json: async () => ({ code: "MODEL_UNAVAILABLE", user_message: "测试模型不可用", retryable: true }) };
    }
    return response([]);
  }));
  const user = userEvent.setup(); render(<App/>);
  await user.click(screen.getByRole("button", { name: "代码库" }));
  await user.click(await screen.findByRole("button", { name: "main.py" }));
  await waitFor(() => expect(screen.getByLabelText("源码阅读区")).toHaveTextContent("square"));
  expect(screen.queryByLabelText("来源模式")).not.toBeInTheDocument();
  expect(screen.getByLabelText("学习问题")).toHaveValue("");
  await user.type(screen.getByLabelText("学习问题"), "解释 square 的计算过程");
  await user.click(screen.getByRole("button", { name: "发送" }));
  await waitFor(() => expect(sent?.scope.repository_allowlist).toEqual(["fixture/code"]));
  expect(sent.scope.network_authorized).toBe(false);
  expect(screen.getByLabelText("学习问题")).toHaveValue("解释 square 的计算过程");
  await user.click(screen.getByRole("button", { name: "文档" }));
  expect(screen.getByLabelText("来源模式")).toHaveValue("public_search");
  expect(screen.getByRole("button", { name: "发送" })).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "代码库" }));
  await waitFor(() => expect(screen.getByLabelText("源码阅读区")).toBeVisible());
  await waitFor(() => expect(screen.getByRole("button", { name: "发送" })).toBeEnabled());
});


test("saved code notes retain fixed file and line links without a network reread", async () => {
  const note = { note_id: "saved-code", title: "平方函数笔记", revision: 1, user_text: "我的理解",
    code_evidence_snapshot: [], explanation_snapshot: { answer_sections: [{ title: "从代码理解", text: "将输入乘以自身。" }],
      context_snapshot: { source_type: "CODE", relevant_context_blocks: unit.blocks },
      document_citations: [{ block_id: "code-block", quote: "    return x * x" }] } };
  vi.stubGlobal("fetch", vi.fn(async (url) => {
    if (url.endsWith("/notes/saved-code")) return response(note);
    if (url.includes("/notes")) return response({ notes: [note], total: 1 });
    if (url.includes("/sessions")) return response({ session_id: "notes-session", context_revision: 0 });
    if (url.endsWith("/documents")) return response({ documents: [] });
    if (url.endsWith("/capabilities")) return response({ tutor: { available: false } });
    return response([]);
  }));
  const user = userEvent.setup(); render(<App/>);
  await user.click(await screen.findByRole("button", { name: "笔记 1" }));
  await user.click(screen.getByRole("button", { name: "平方函数笔记 修订 1" }));
  await user.click(await screen.findByText("冻结的讲解与来源"));
  expect(screen.getByRole("link", { name: "在 GitHub 查看 src/main.py 第 3 至 3 行" })).toHaveAttribute("href",
    "https://github.com/fixture/code/blob/" + repo.commit_sha + "/src/main.py#L3-L3");
  expect(fetch.mock.calls.some(([url]) => url.includes("/files?") || url.includes("/repositories/"))).toBe(false);
});
