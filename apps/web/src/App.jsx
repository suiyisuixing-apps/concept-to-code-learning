import { useEffect, useRef, useState } from "react";
import { api, hashText } from "./api.js";

function Evidence({ source }) {
  if (!source)
    return (
      <div className="empty-state">
        <h3>让代码支持你的理解</h3>
        <p>
          提出依赖注入的问题后，这里会显示已核验的 FastAPI 官方示例和引用位置。
        </p>
        <p className="muted">
          演示仅包含一条冻结来源。实时搜索与通用核验待实现。
        </p>
      </div>
    );
  const link = `${source.repository_url}/blob/${source.commit_sha}/${source.file_path}#L${source.line_start}-L${source.line_end}`;
  return (
    <article className="evidence">
      <div className="source-heading">
        <a href={source.repository_url} target="_blank" rel="noreferrer">
          {source.repository_owner} / {source.repository_name}
        </a>
        <span className="small-label">公开仓库</span>
      </div>
      <p className="verification">固定来源已核验</p>
      <p className="machine-status">{source.verification_status}</p>
      <dl className="source-details">
        <dt>仓库</dt>
        <dd>
          <a href={source.repository_url} target="_blank" rel="noreferrer">
            {source.repository_url}
          </a>
        </dd>
        <dt>Commit</dt>
        <dd className="commit">{source.commit_sha}</dd>
        <dt>文件</dt>
        <dd>
          <a href={link} target="_blank" rel="noreferrer">
            {source.file_path}
          </a>
        </dd>
        <dt>符号</dt>
        <dd>
          <code>{source.symbol}</code>
        </dd>
        <dt>行号</dt>
        <dd>
          {source.line_start}–{source.line_end} · {source.symbol_type}
        </dd>
        <dt>许可证</dt>
        <dd>
          <a href={source.license_url} target="_blank" rel="noreferrer">
            {source.license_name}
          </a>
        </dd>
      </dl>
      <div className="code-heading">
        <span>GitHub 原始代码 · 3 行</span>
        <a href={link} target="_blank" rel="noreferrer">
          打开源码
        </a>
      </div>
      <pre aria-label="GitHub 原始代码">
        <code>{source.code_excerpt}</code>
      </pre>
      <h3>为什么引用它</h3>
      <p>{source.relevance_reason}</p>
      <p className="muted">
        片段未运行 · NOT_RUN
        <br />
        核验时间：{source.retrieved_at.slice(0, 10)}
      </p>
      <details>
        <summary>查看核验依据</summary>
        <p>{source.verification_method}</p>
        <p className="commit">片段 SHA-256：{source.excerpt_hash}</p>
      </details>
    </article>
  );
}

export default function App() {
  const [session, setSession] = useState(null);
  const [notes, setNotes] = useState([]);
  const [page, setPage] = useState(0);
  const [selection, setSelection] = useState("");
  const [question, setQuestion] = useState("");
  const [level, setLevel] = useState("Beginner");
  const [answer, setAnswer] = useState(null);
  const [view, setView] = useState("learn");
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [title, setTitle] = useState("依赖注入：我的理解");
  const [userText, setUserText] = useState("");
  const passage = useRef(null);

  async function load() {
    setError("");
    try {
      const [health, demo, saved] = await Promise.all([
        api("/health"),
        api("/api/demo/session"),
        api("/api/notes"),
      ]);
      if (health.health !== "ok" || demo.mode !== "FIXTURE")
        throw new Error("本地演示状态不匹配，请重启服务。");
      setSession(demo);
      setQuestion(demo.question);
      setNotes(saved.notes);
    } catch (err) {
      setError(err.message);
    }
  }
  useEffect(() => {
    load();
  }, []);

  if (!session)
    return (
      <main className="startup">
        <h1>Concept-to-Code Learning</h1>
        {error ? (
          <>
            <p role="alert">{error}</p>
            <button onClick={load}>重新连接</button>
          </>
        ) : (
          <p role="status">正在连接本地学习空间…</p>
        )}
      </main>
    );
  const current = session.document.pages[page];

  function changePage(index) {
    setPage(index);
    setSelection("");
  }
  function captureSelection() {
    const range = window.getSelection();
    if (
      range &&
      passage.current?.contains(range.anchorNode) &&
      passage.current?.contains(range.focusNode)
    ) {
      setSelection(range.toString().trim());
    }
  }
  async function explain(selected = selection) {
    if (busy || !question.trim()) return;
    setBusy(true);
    setError("");
    setNotice("");
    setView("learn");
    try {
      const context = {
        ...session.document_context,
        current_page: current.page,
        current_section: current.section,
        selected_text: selected,
        selected_text_hash: await hashText(selected),
      };
      setAnswer(
        await api("/api/learning/explain", {
          question,
          document_context: context,
          explanation_level: level,
        }),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  async function save() {
    if (!answer || saving || !title.trim()) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const note = await api("/api/notes", {
        grounded_explanation_id: answer.grounded_explanation_id,
        title,
        user_text: userText,
        save_requested_by_user: true,
      });
      setNotes((items) => [note, ...items]);
      setNotice("笔记已保存到本地，包含文档引用和 GitHub 来源。");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <header className="app-header">
        <div className="identity">
          <svg viewBox="0 0 32 32" aria-hidden="true">
            <path d="M5 7h9c2 0 3 1 3 3v17c0-2-1-3-3-3H5zM27 7h-7M22 13l-3 3 3 3M26 13l3 3-3 3" />
          </svg>
          <div>
            <h1>
              Concept-to-Code <span>Learning</span>
            </h1>
            <p>读懂概念，找到真实代码</p>
          </div>
        </div>
        <div className="header-state">
          <span className="local-state">本地演示已连接</span>
          <span className="fixture-label">FIXTURE</span>
        </div>
      </header>
      <div className="demo-banner">
        <strong>合成讲义 + 固定讲解</strong>
        <span>
          体验从阅读到来源笔记的完整流程。未接入 AI 模型、真实文件导入或实时
          GitHub 搜索。
        </span>
        <code>SCAFFOLD_DEMO</code>
      </div>
      <main className="workspace">
        <section
          className="pane document-pane"
          aria-labelledby="document-heading"
        >
          <div className="pane-title">
            <h2 id="document-heading">文档学习区</h2>
            <span>合成示例</span>
          </div>
          <div className="document-meta">
            <h3>{session.document.file_name}</h3>
            <p>Markdown Fixture · 共 {session.document.pages.length} 页</p>
          </div>
          <nav className="pagination" aria-label="文档翻页">
            <button
              aria-label="上一页"
              disabled={page === 0}
              onClick={() => changePage(page - 1)}
            >
              上一页
            </button>
            <span>
              第 {page + 1} / {session.document.pages.length} 页
            </span>
            <button
              aria-label="下一页"
              disabled={page === session.document.pages.length - 1}
              onClick={() => changePage(page + 1)}
            >
              下一页
            </button>
          </nav>
          <article
            ref={passage}
            className="document-page"
            tabIndex={0}
            aria-label="可选择的当前页正文"
            onMouseUp={captureSelection}
            onKeyUp={captureSelection}
          >
            <h3>{current.title}</h3>
            {current.paragraphs.map((text) => (
              <p key={text}>{text}</p>
            ))}
          </article>
          <div className="selection-context">
            <label htmlFor="selected-passage">选中文字</label>
            <textarea
              id="selected-passage"
              rows={3}
              value={selection}
              onChange={(e) => setSelection(e.target.value)}
              placeholder="在正文中选中一句话，或粘贴当前页原文。"
            />
            <div className="action-row">
              <button
                className="secondary"
                disabled={busy || !question.trim()}
                onClick={() => explain("")}
              >
                解释当前页
              </button>
              <button
                disabled={busy || !question.trim() || !selection.trim()}
                onClick={() => explain(selection)}
              >
                解释选中文字
              </button>
            </div>
            {!question.trim() && <p className="muted">先在学习助手中输入问题，再开始讲解。</p>}
          </div>
          <p className="import-note">
            PDF、PPTX、DOCX 导入将在后续任务中提供。
          </p>
        </section>
        <section className="pane tutor-pane" aria-labelledby="tutor-heading">
          <div className="pane-title">
            <h2 id="tutor-heading">AI 学习助手</h2>
            <nav className="view-tabs" aria-label="学习与笔记">
              <button
                aria-pressed={view === "learn"}
                onClick={() => setView("learn")}
              >
                讲解
              </button>
              <button
                aria-pressed={view === "notes"}
                onClick={() => setView("notes")}
              >
                我的笔记 ({notes.length})
              </button>
            </nav>
          </div>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          {notice && (
            <p className="notice" role="status">
              {notice}
            </p>
          )}
          {view === "notes" ? (
            <div className="notes-list">
              <h3>我的来源笔记</h3>
              <p className="muted">
                只有点击保存才会新增笔记；已有内容会保留。
              </p>
              {!notes.length && (
                <p>
                  还没有笔记。先提出问题，再把讲解、来源和自己的理解一起保存。
                </p>
              )}
              {notes.map((note) => (
                <article className="saved-note" key={note.note_id}>
                  <h3>{note.title}</h3>
                  <p className="user-note">
                    {note.user_text || "未添加个人文字"}
                  </p>
                  <details>
                    <summary>已保存的讲解与来源</summary>
                    <p className="answer-text">
                      {note.grounded_explanation.explanation}
                    </p>
                    {note.document_sources.map((doc) => (
                      <blockquote key={doc.quote_hash}>
                        {doc.file_name} · 第 {doc.page} 页<p>{doc.quote}</p>
                      </blockquote>
                    ))}
                    {note.github_sources.map((source) => (
                      <Evidence key={source.source_id} source={source} />
                    ))}
                  </details>
                  <time dateTime={note.created_at}>
                    {new Date(note.created_at).toLocaleString("zh-CN")}
                  </time>
                </article>
              ))}
            </div>
          ) : (
            <>
              <form
                className="question-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  explain();
                }}
              >
                <label htmlFor="question">你想理解什么？</label>
                <textarea
                  id="question"
                  rows={3}
                  maxLength={2000}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                />
                <p className="question-context">
                  当前上下文：第 {current.page} 页 ·{" "}
                  {selection ? "选中文字" : current.section}
                </p>
                <div className="ask-controls">
                  <div>
                    <label htmlFor="level">解释难度</label>
                    <select
                      id="level"
                      value={level}
                      onChange={(e) => setLevel(e.target.value)}
                    >
                      {session.explanation_levels.map((item) => (
                        <option key={item}>{item}</option>
                      ))}
                    </select>
                  </div>
                  <button type="submit" disabled={busy || !question.trim()}>
                    {busy ? "正在整理讲解…" : "结合代码讲解"}
                  </button>
                </div>
              </form>
              {busy && (
                <p className="loading" role="status">
                  正在读取当前上下文和冻结来源…
                </p>
              )}
              {answer ? (
                <article className="answer">
                  <div className="answer-heading">
                    <h3>{answer.concept.name}</h3>
                    <span>{answer.explanation_level} · 固定讲解</span>
                  </div>
                  <p className="answered-question">问题：{answer.question}</p>
                  <p className="answer-text">{answer.explanation}</p>
                  <div className="document-citations">
                    <h4>文档依据</h4>
                    {answer.document_citations.map((doc) => (
                      <blockquote key={doc.quote_hash}>
                        <cite>
                          {doc.file_name} · 第 {doc.page} 页
                        </cite>
                        <p>{doc.quote}</p>
                      </blockquote>
                    ))}
                  </div>
                  <p className="muted">
                    右侧为本次引用的真实代码。讲解为人工编写的
                    Fixture，未调用模型。
                  </p>
                  <div className="save-note">
                    <h3>记下自己的理解</h3>
                    <label htmlFor="note-title">笔记标题</label>
                    <input
                      id="note-title"
                      maxLength={160}
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                    />
                    <label htmlFor="note-text">我的补充</label>
                    <textarea
                      id="note-text"
                      rows={3}
                      maxLength={20000}
                      value={userText}
                      onChange={(e) => setUserText(e.target.value)}
                      placeholder="用自己的话记下这个概念。再次提问不会清除这里的文字。"
                    />
                    <button
                      onClick={save}
                      disabled={saving || busy || !title.trim()}
                    >
                      {saving ? "正在保存…" : "保存为学习笔记"}
                    </button>
                    <p className="muted">
                      同时保存本次讲解、文档引用与 GitHub 来源。
                    </p>
                  </div>
                </article>
              ) : (
                <div className="empty-state">
                  <h3>从一个问题开始</h3>
                  <p>
                    试试左侧的依赖注入讲义。选择难度，然后查看概念如何落到真实代码里。
                  </p>
                  <p className="muted">
                    此演示仅回答依赖注入主题；其他问题会提示证据不足。
                  </p>
                </div>
              )}
            </>
          )}
        </section>
        <aside
          className="pane evidence-pane"
          aria-labelledby="evidence-heading"
        >
          <div className="pane-title">
            <h2 id="evidence-heading">GitHub 代码证据</h2>
            <span>{answer ? "1 条来源" : "等待提问"}</span>
          </div>
          <Evidence source={answer?.github_sources[0]} />
        </aside>
      </main>
      <footer className="app-footer">
        <span>数据保存在当前本地演示空间</span>
        <span>Concept-to-Code Learning · 0.2.0.dev0</span>
      </footer>
    </>
  );
}
