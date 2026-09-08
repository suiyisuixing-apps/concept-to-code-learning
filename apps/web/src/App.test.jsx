import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import App from "./App.jsx";
import document from "../../../demo/learning/document.json";
import source from "../../../demo/learning/github-source.json";

test("blank questions disable all explain actions with recovery guidance", async () => {
  const user = userEvent.setup();
  render(<App />);
  await user.clear(await screen.findByLabelText("你想理解什么？"));
  await user.type(screen.getByLabelText("选中文字"), "依赖注入");
  for (const name of ["解释当前页", "解释选中文字", "结合代码讲解"]) {
    expect(screen.getByRole("button", { name, exact: true })).toBeDisabled();
  }
  expect(screen.getByText("先在学习助手中输入问题，再开始讲解。")).toBeVisible();
  await user.type(screen.getByLabelText("你想理解什么？"), "依赖注入是什么？");
  expect(screen.getByRole("button", { name: "解释选中文字", exact: true })).toBeEnabled();
});

let saved;
let lastRequest;
let failExplain;
beforeEach(() => {
  saved = [];
  lastRequest = null;
  failExplain = false;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path, options) => {
      const body = options?.body ? JSON.parse(options.body) : undefined;
      let value;
      let ok = true;
      if (path === "/health") value = { health: "ok", mode: "FIXTURE" };
      if (path === "/api/demo/session")
        value = {
          mode: "FIXTURE",
          status: "SCAFFOLD_DEMO",
          document,
          question: "依赖注入到底是什么？真实项目中怎么使用？",
          explanation_levels: [
            "Beginner",
            "University",
            "Engineering",
            "Source-code level",
          ],
          document_context: {
            document_id: document.document_id,
            file_name: document.file_name,
            source_type: "MARKDOWN_FIXTURE",
            current_page: 1,
            current_slide: null,
            current_section: document.pages[0].section,
            selected_text: "",
            selected_text_hash: null,
          },
        };
      if (path === "/api/learning/explain") {
        lastRequest = body;
        if (failExplain) {
          ok = false;
          value = { detail: "NEEDS_CONFIRMATION: 当前选区不在页面中" };
        } else
          value = {
            ...body,
            grounded_explanation_id: "explanation-one",
            concept: { name: "依赖注入" },
            explanation: "由框架提供依赖，函数使用注入的参数。",
            github_sources: [source],
            document_citations: [
              {
                file_name: document.file_name,
                page: body.document_context.current_page,
                quote:
                  body.document_context.selected_text ||
                  document.pages[0].paragraphs[0],
                quote_hash: "one",
              },
            ],
          };
      }
      if (path === "/api/notes" && !body) value = { notes: saved };
      if (path === "/api/notes" && body) {
        value = {
          ...body,
          note_id: String(saved.length + 1),
          created_at: "2026-09-07T00:00:00Z",
          document_sources: [],
          github_sources: [source],
          grounded_explanation: { explanation: "saved" },
        };
        saved = [value, ...saved];
      }
      return { ok, json: async () => value };
    }),
  );
});

test("shows truthful fixture and all three functional panes", async () => {
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "文档学习区" }),
  ).toBeVisible();
  expect(screen.getByRole("heading", { name: "AI 学习助手" })).toBeVisible();
  expect(
    screen.getByRole("heading", { name: "GitHub 代码证据" }),
  ).toBeVisible();
  expect(screen.getByText("SCAFFOLD_DEMO")).toBeVisible();
  expect(screen.getByRole("button", { name: "上一页" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "解释选中文字" })).toBeDisabled();
  expect(screen.getByText(/未接入 AI 模型/)).toBeVisible();
});

test("page and selected text with hash reach backend and source is shown", async () => {
  const user = userEvent.setup();
  render(<App />);
  await user.click(await screen.findByRole("button", { name: "下一页" }));
  await user.type(
    screen.getByLabelText("选中文字"),
    document.pages[1].paragraphs[0],
  );
  await user.selectOptions(screen.getByLabelText("解释难度"), "University");
  await user.click(screen.getByRole("button", { name: "解释选中文字" }));
  expect(await screen.findByText(source.commit_sha)).toBeVisible();
  expect(lastRequest.document_context.current_page).toBe(2);
  expect(lastRequest.document_context.selected_text).toBe(
    document.pages[1].paragraphs[0],
  );
  expect(lastRequest.document_context.selected_text_hash).toMatch(
    /^[a-f0-9]{64}$/,
  );
  expect(lastRequest.explanation_level).toBe("University");
  expect(screen.getByRole("link", { name: "打开源码" })).toHaveAttribute(
    "href",
    expect.stringContaining("#L12-L14"),
  );
  await user.click(screen.getByRole("button", { name: "下一页" }));
  expect(screen.getByLabelText("选中文字")).toHaveValue("");
});

test("saving is explicit, reload reads persisted notes, asking preserves user text", async () => {
  const user = userEvent.setup();
  const first = render(<App />);
  await user.click(await screen.findByRole("button", { name: "结合代码讲解" }));
  await user.type(
    await screen.findByLabelText("我的补充"),
    "我的理解不会被 AI 覆盖",
  );
  expect(saved).toHaveLength(0);
  await user.click(screen.getByRole("button", { name: "结合代码讲解" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "保存为学习笔记" }),
    ).toBeEnabled(),
  );
  expect(screen.getByLabelText("我的补充")).toHaveValue(
    "我的理解不会被 AI 覆盖",
  );
  await user.click(screen.getByRole("button", { name: "保存为学习笔记" }));
  expect(await screen.findByText(/笔记已保存到本地/)).toBeVisible();
  expect(saved[0].save_requested_by_user).toBe(true);
  expect(saved[0].user_text).toBe("我的理解不会被 AI 覆盖");
  first.unmount();
  render(<App />);
  await user.click(await screen.findByRole("button", { name: "我的笔记 (1)" }));
  expect(screen.getByText("我的理解不会被 AI 覆盖")).toBeVisible();
});

test("failed answer is visible and cannot create a note", async () => {
  failExplain = true;
  const user = userEvent.setup();
  render(<App />);
  await user.click(await screen.findByRole("button", { name: "结合代码讲解" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "NEEDS_CONFIRMATION",
  );
  expect(screen.queryByRole("button", { name: "保存为学习笔记" })).toBeNull();
  expect(saved).toHaveLength(0);
});
