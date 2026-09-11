import { useEffect, useRef, useState } from "react";
import { api, hashText, id, json } from "./api.js";
import Reader from "./Reader.jsx";
import Annotations, { useAnnotations } from "./Annotations.jsx";
import { questionForSelection, selectionKey } from "./selection.js";

const levels = ["Beginner", "University", "Engineering", "Source-code"];

function ErrorBox({ error, retry }) {
  if (!error) return null;
  return <div className="error" role="alert"><strong>{error.code}</strong><span>{error.message}</span>
    {error.neededAction && <small>{error.neededAction}</small>}
    {error.retryable && retry && <button onClick={retry}>重试</button>}</div>;
}

function SourceCard({ source }) {
  return <article className="source-card"><header><strong>{source.repository_owner ? `${source.repository_owner}/${source.repository_name}` : source.local_handle}</strong><span>{source.verification_status}</span></header>
    <dl><dt>位置</dt><dd>{source.file_path}:{source.line_start}-{source.line_end}</dd><dt>{source.dirty ? "未提交版本" : "版本"}</dt><dd><code>{source.dirty ? source.file_sha256 : source.commit_sha || source.file_sha256 || "本地内容"}</code>{source.dirty && <small>当前文件 SHA-256；正文包含未提交修改。</small>}</dd><dt>许可</dt><dd>{source.license_observation.status}{source.license_observation.files?.map((file) => <div key={file.path}>{file.permalink ? <a href={file.permalink} target="_blank" rel="noreferrer">{file.identifier || "未识别"} · {file.path}</a> : <span>{file.identifier || "未识别"} · {file.path}</span>}</div>)}</dd><dt>运行</dt><dd>{source.execution_status === "NOT_RUN" ? "未运行" : source.execution_status}</dd></dl>
    {source.code_excerpt ? <pre aria-label="已核验原始代码"><code>{source.code_excerpt}</code></pre> : <p className="boundary">许可不明确，服务端未返回源码正文。</p>}
    {source.permalink && <a href={source.permalink} target="_blank" rel="noreferrer">打开固定版本源码</a>}<p>{source.relevance.reason}</p></article>;
}

function Notes({ notes, query, setQuery, report, changed, removed }) {
  const [active, setActive] = useState(null), [draft, setDraft] = useState({ title: "", user_text: "" });
  const [pending, setPending] = useState(false);
  const opening = useRef(0), mutating = useRef(false);
  useEffect(() => () => { opening.current++; }, []);
  async function open(note) {
    if (mutating.current) return;
    const epoch = ++opening.current;
    try {
      const value = await api(`/notes/${note.note_id}`);
      if (epoch !== opening.current) return;
      setActive(value); setDraft({ title: value.title, user_text: value.user_text });
    } catch (e) { if (epoch === opening.current) report(e); }
  }
  async function edit() {
    if (!active || mutating.current || !draft.title.trim()) return;
    mutating.current = true; opening.current++; setPending(true);
    try {
      const value = await api(`/notes/${active.note_id}`, json("PATCH", { expected_revision: active.revision, ...draft }));
      setActive(value); changed(value);
    } catch (e) { report(e); } finally { mutating.current = false; setPending(false); }
  }
  async function remove() {
    if (!active || mutating.current || !confirm("确认删除这条笔记？")) return;
    mutating.current = true; opening.current++; setPending(true);
    try {
      await api(`/notes/${active.note_id}`, json("DELETE", { expected_revision: active.revision, confirmed_by_user: true }));
      removed(active.note_id); setActive(null);
    } catch (e) { report(e); } finally { mutating.current = false; setPending(false); }
  }
  return <div className="notes"><input aria-label="搜索笔记" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索笔记"/>{notes.map((note) => <button className="note-row" key={note.note_id} onClick={() => open(note)}><strong>{note.title}</strong><span>修订 {note.revision}</span></button>)}{!notes.length && <p className="empty">没有匹配笔记。</p>}
    {active && <section className="note-editor"><p>冻结来源 · 修订 {active.revision}</p><input maxLength={160} aria-label="笔记标题" disabled={pending} value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })}/><textarea maxLength={20000} aria-label="个人笔记" disabled={pending} value={draft.user_text} onChange={(e) => setDraft({ ...draft, user_text: e.target.value })}/><div className="row"><button disabled={pending || !draft.title.trim()} onClick={edit}>{pending ? "保存中…" : "保存修改"}</button><a href={`/api/learning/v1/notes/${active.note_id}/export?format=markdown`}>Markdown</a><a href={`/api/learning/v1/notes/${active.note_id}/export?format=json`}>JSON</a><button className="danger" disabled={pending} onClick={remove}>删除</button></div><details><summary>冻结的讲解与来源</summary>{active.explanation_snapshot.answer_sections.map((x) => <p key={x.title}><strong>{x.title}</strong><br/>{x.text}</p>)}{active.code_evidence_snapshot.map((x) => <SourceCard key={x.source_id} source={x}/>)}</details></section>}
  </div>;
}

export default function App() {
  const [caps, setCaps] = useState(null);
  const [session, setSession] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [record, setRecord] = useState(null);
  const [units, setUnits] = useState([]);
  const [unit, setUnit] = useState(null);
  const [selection, setSelection] = useState(null);
  const [question, setQuestion] = useState("");
  const [level, setLevel] = useState("Beginner");
  const [scopeMode, setScopeMode] = useState("specified_public");
  const [repository, setRepository] = useState("");
  const [localHandles, setLocalHandles] = useState([]);
  const [localHandle, setLocalHandle] = useState("");
  const [network, setNetwork] = useState(false);
  const [approved, setApproved] = useState(false);
  const [terms, setTerms] = useState("");
  const [advanced, setAdvanced] = useState(false);
  const [compare, setCompare] = useState(false);
  const [result, setResult] = useState(null);
  const [chosen, setChosen] = useState([]);
  const [busy, setBusy] = useState(false);
  const [contextBusy, setContextBusy] = useState(false);
  const [importing, setImporting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState("");
  const [tab, setTab] = useState("sources");
  const [notes, setNotes] = useState([]);
  const [noteQuery, setNoteQuery] = useState("");
  const [noteTotal, setNoteTotal] = useState(0);
  const [noteText, setNoteText] = useState("");
  const active = useRef(null);
  const sessionRef = useRef(null);
  const saveKey = useRef(null);
  const savingRef = useRef(false);
  const loadingMore = useRef(false);
  const contextEpoch = useRef(0);
  const contextQueue = useRef(Promise.resolve());
  const retry = useRef(null);
  const noteEpoch = useRef(0);
  const mounted = useRef(false);
  const questionInput = useRef(null), questionRef = useRef(""), autoQuestion = useRef("");
  const selectionRequest = useRef("");
  questionRef.current = question;
  const explanation = result?.explanation;
  const annotations = useAnnotations(record, unit, report, setNotice);

  function rememberSession(value) { sessionRef.current = value; setSession(value); }
  function report(e, action) { setError(e); retry.current = action; }
  async function refreshCapabilities() {
    try { setCaps(await api("/capabilities")); } catch (e) { report(e, refreshCapabilities); }
  }
  useEffect(() => {
    mounted.current = true;
    let live = true;
    (async () => {
      const loaded = await Promise.allSettled([
        api("/capabilities"), api("/sessions", { method: "POST" }), api("/documents"),
        api("/notes"), api("/sources/local-handles"),
      ]);
      if (!live) return;
      if (loaded[0].status === "fulfilled") setCaps(loaded[0].value);
      if (loaded[1].status === "fulfilled") rememberSession(loaded[1].value);
      if (loaded[2].status === "fulfilled") setDocuments(loaded[2].value.documents);
      if (loaded[3].status === "fulfilled") {
        setNotes(loaded[3].value.notes); setNoteTotal(loaded[3].value.total || loaded[3].value.notes.length);
      }
      if (loaded[4].status === "fulfilled" && Array.isArray(loaded[4].value)) {
        setLocalHandles(loaded[4].value); setLocalHandle(loaded[4].value[0] || "");
      }
      const failed = loaded.find((x) => x.status === "rejected");
      if (failed) report(failed.reason, () => window.location.reload());
      if (loaded[1].status === "fulfilled" && loaded[2].status === "fulfilled"
          && loaded[2].value.documents[0]) await openDocument(loaded[2].value.documents[0]);
    })();
    return () => { live = false; mounted.current = false; contextEpoch.current++; active.current?.controller.abort(); };
  }, []);

  useEffect(() => {
    if (!session) return;
    const epoch = ++noteEpoch.current;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const value = await api(`/notes?q=${encodeURIComponent(noteQuery)}`, { signal: controller.signal });
        if (epoch === noteEpoch.current) { setNotes(value.notes); setNoteTotal(value.total ?? value.notes.length); }
      } catch (e) { if (e.name !== "AbortError") report(e, () => setNoteQuery((v) => v + " ")); }
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [noteQuery, session?.session_id]);

  function stopActive() {
    const pending = active.current;
    active.current = null;
    setBusy(false);
    if (pending) {
      pending.controller.abort();
      // Context activation also invalidates the server epoch. This request frees work promptly.
      api(`/requests/${pending.requestId}?session_id=${pending.sessionId}`, { method: "DELETE" }).catch(() => {});
    }
  }
  function beginContextChange() {
    stopActive();
    selectionRequest.current = "";
    const epoch = ++contextEpoch.current;
    setContextBusy(true); setChosen([]); setNotice(""); setError(null);
    return epoch;
  }
  function activate(doc, list, target, value, epoch) {
    contextQueue.current = contextQueue.current.catch(() => {}).then(async () => {
      if (epoch !== contextEpoch.current || !mounted.current) return;
      const current = sessionRef.current;
      if (!current) return;
      try {
        const next = await api(`/sessions/${current.session_id}/context`, json("POST", {
          document_id: doc.document_id, document_revision: doc.revision, unit_id: target.unit_id,
          selected_text: value?.text || "", selected_text_hash: value ? await hashText(value.text) : null,
          selection_locator: value ? { spans: value.spans, normalization: "exact" } : null,
          expected_context_revision: current.context_revision,
        }));
        sessionRef.current = next;
        if (epoch === contextEpoch.current && mounted.current) {
          rememberSession(next); setRecord(doc); setUnits(list); setUnit(target);
          setSelection(value); setResult(null); setChosen([]); saveKey.current = null;
          if (!value && questionRef.current === autoQuestion.current) {
            autoQuestion.current = ""; questionRef.current = ""; setQuestion("");
          }
          return next;
        }
      } catch (e) {
        // Recover the authoritative revision after a concurrent request or response loss.
        try { sessionRef.current = await api(`/sessions/${current.session_id}`); } catch { /* retain input */ }
        if (epoch === contextEpoch.current) { selectionRequest.current = ""; setSession(null); report(e, () => navigate(doc, list, list.indexOf(target))); }
      } finally {
        if (epoch === contextEpoch.current && mounted.current) setContextBusy(false);
      }
    });
    return contextQueue.current;
  }
  async function openDocument(doc) {
    if (!doc) return;
    const epoch = beginContextChange();
    try {
      const list = (await api(`/documents/${doc.document_id}/units`)).units;
      if (epoch !== contextEpoch.current) return;
      if (!list.length) throw new Error("此文档没有可阅读单元，请重新导入。");
      await activate(doc, list, list[0], null, epoch);
    } catch (e) {
      if (epoch === contextEpoch.current) { setContextBusy(false); report(e, () => openDocument(doc)); }
    }
  }
  async function navigate(doc, list, index) {
    if (!list[index]) return;
    return activate(doc, list, list[index], null, beginContextChange());
  }
  async function chooseSelection(value) {
    if (!unit || !record) return;
    if (value && Array.from(value.text).length > 10000) {
      report(new Error("选中文字过长，请缩小到 10,000 字以内。")); return;
    }
    if (value?.spans.length > 50) { report(new Error("选区跨越的段落过多，请缩小到 50 段以内。")); return; }
    const key = `${record.document_id}:${unit.unit_id}:${selectionKey(value)}`;
    if (selectionRequest.current === key || (!contextBusy && selectionKey(value) === selectionKey(selection))) return;
    const epoch = beginContextChange(); selectionRequest.current = key;
    const next = await activate(record, units, unit, value, epoch);
    if (next && value && epoch === contextEpoch.current) {
      if (!questionRef.current.trim() || questionRef.current === autoQuestion.current) {
        autoQuestion.current = questionForSelection(value); questionRef.current = autoQuestion.current; setQuestion(autoQuestion.current);
      }
      setNotice("原句已引用到对话框，可编辑问题或为这段话写批注。");
    }
    return next;
  }
  function editQuestion(replace = false) {
    if (replace && selection) { autoQuestion.current = questionForSelection(selection); questionRef.current = autoQuestion.current; setQuestion(autoQuestion.current); }
    questionInput.current?.focus({ preventScroll: true });
    questionInput.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }
  function writeAnnotation() { if (annotations.start(selection)) setTab("annotations"); }
  function openAnnotation(value) { if (annotations.open(value)) setTab("annotations"); }
  async function locateAnnotation(value) {
    if (value.anchor.document_revision !== record?.revision || value.anchor.original_sha256 !== record?.original_sha256) {
      setNotice("这条批注属于另一个文档版本，请核对原文后再引用。"); return;
    }
    const target = units.find((x) => x.unit_id === value.anchor.unit_id);
    if (!target) return;
    const quote = { text: value.anchor.selected_text, spans: value.anchor.selection_locator.spans, reveal: true };
    if (unit.unit_id === target.unit_id && selectionKey(selection) === selectionKey(quote)) setSelection(quote);
    else await activate(record, units, target, quote, beginContextChange());
  }
  async function importFile(file) {
    if (importing) return;
    setImporting(true); setError(null);
    try {
      if (file.size > 20 * 1024 * 1024) throw new Error("文件超过 20 MB，请拆分后导入。");
      const value = await api(`/documents?file_name=${encodeURIComponent(file.name)}`, {
        method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: file,
      });
      setDocuments((items) => [value, ...items.filter((d) => d.document_id !== value.document_id)]);
      await openDocument(value);
    } catch (e) { report(e, () => importFile(file)); } finally { setImporting(false); }
  }
  function scope() {
    const values = terms.split(/[,，\n]/).map((x) => x.trim()).filter(Boolean);
    const repos = repository.split(/[,，\n]/).map((x) => x.trim().replace(/^https:\/\/github\.com\//, "").replace(/\/$/, "")).filter(Boolean);
    return { source_mode: scopeMode, repository_allowlist: scopeMode === "specified_public" ? repos : [],
      local_handle: scopeMode === "local_authorized" ? localHandle || null : null,
      language_hint: null, scope_limit: { repositories: 5, files: 10 },
      network_authorized: scopeMode !== "local_authorized" && network,
      query_terms_approved: approved, approved_query_terms: values, max_sources: compare ? 2 : 3 };
  }
  async function ask({ followup = false, useCandidates = false } = {}) {
    if (!question.trim() || !session?.context_revision || !sessionRef.current?.context_revision || contextBusy || active.current) return;
    const requestId = id(), current = sessionRef.current, controller = new AbortController();
    const epoch = contextEpoch.current;
    active.current = { requestId, sessionId: current.session_id, controller };
    setBusy(true); setError(null); setNotice("");
    try {
      const value = await api("/explanations", { ...json("POST", {
        request_id: requestId, session_id: current.session_id, context_revision: current.context_revision,
        question: question.trim(), level, scope: scope(), source_ids: [],
        candidate_ids: useCandidates ? chosen : [], query_id: useCandidates ? result?.query_id : null,
        compare, continue_from: followup ? explanation?.explanation_id || null : null,
      }), signal: controller.signal });
      if (active.current?.requestId === requestId && epoch === contextEpoch.current) {
        saveKey.current = null; setResult(value); setChosen([]);
      }
    } catch (e) {
      if (active.current?.requestId === requestId && e.name !== "AbortError") report(e, () => ask({ followup, useCandidates }));
    } finally {
      if (active.current?.requestId === requestId) { active.current = null; setBusy(false); }
    }
  }
  function changeScope(action) { stopActive(); setChosen([]); if (result?.candidates?.length) setResult(null); action(); }
  function cancel() { stopActive(); setNotice("已取消；问题输入仍保留。"); }
  async function saveNote() {
    if (!explanation || savingRef.current) return;
    if (!saveKey.current) saveKey.current = id("save");
    savingRef.current = true; setSaving(true);
    try {
      const value = await api("/notes", json("POST", { session_id: sessionRef.current.session_id,
        explanation_id: explanation.explanation_id, idempotency_key: saveKey.current,
        save_requested_by_user: true, title: explanation.question.slice(0, 160), user_text: noteText }));
      noteEpoch.current++;
      setNotes((items) => [value, ...items.filter((n) => n.note_id !== value.note_id)]);
      setNotice("笔记已保存。后续修改可在右侧「笔记」中编辑。");
    } catch (e) { report(e, saveNote); } finally { savingRef.current = false; setSaving(false); }
  }
  async function moreNotes() {
    if (loadingMore.current) return;
    loadingMore.current = true;
    const epoch = noteEpoch.current;
    try {
      const value = await api(`/notes?q=${encodeURIComponent(noteQuery)}&offset=${notes.length}`);
      if (epoch !== noteEpoch.current) return;
      setNotes((items) => [...items, ...value.notes]); setNoteTotal(value.total);
    } catch (e) { if (epoch === noteEpoch.current) report(e, moreNotes); }
    finally { loadingMore.current = false; }
  }
  const sources = [...(result?.sources || []), ...(result?.source_observations || [])];
  const disabled = busy || contextBusy || !question.trim() || !session?.context_revision;
  return <>
    <header className="topbar">
      <div><h1>Concept-to-Code</h1><p>文档学习工作台</p></div>
      <select aria-label="切换文档" value={record?.document_id || ""} onChange={(e) => openDocument(documents.find((x) => x.document_id === e.target.value))}>
        <option value="">选择文档</option>{documents.map((x) => <option value={x.document_id} key={x.document_id}>{x.file_name}</option>)}
      </select>
      <div className={`connection ${caps?.tutor?.available ? "ready" : "partial"}`}><span/>{caps?.tutor?.available ? "模型可用" : "阅读与笔记可用"}</div>
    </header>
    <main className="workspace">
      <Reader record={record} units={units} unit={unit} navigate={(i) => navigate(record, units, i)} select={chooseSelection} selection={selection} importing={importing} importFile={importFile}
        annotations={annotations.highlighted} openAnnotation={openAnnotation} annotate={writeAnnotation} editQuestion={() => editQuestion()} report={report}/>
      <section className="assistant pane" aria-busy={busy || contextBusy}>
        <div className="pane-header"><h2>结合材料与真实代码</h2><span className="context-chip">{contextBusy ? "切换中…" : selection ? "已选文字" : "当前单元"}</span></div>
        <ErrorBox error={error} retry={retry.current}/>
        {notice && <p className="notice" role="status">{notice}</p>}
        {caps?.tutor?.available === false && <div className="setup"><strong>模型尚未配置</strong><p>{caps.tutor.needed_action || "启动本地模型后可生成讲解。"}</p><button onClick={refreshCapabilities}>重新检查模型</button></div>}
        {selection && <div className="selection-summary"><strong>引用原文</strong><blockquote>{selection.text}</blockquote><div className="quote-actions">
          <button onClick={() => editQuestion(true)}>带入问题</button><button disabled={contextBusy} onClick={writeAnnotation}>写批注</button><button disabled={contextBusy} onClick={() => chooseSelection(null)}>清除引用</button></div></div>}
        <label>问题<textarea ref={questionInput} aria-label="学习问题" aria-describedby="question-help" maxLength={2000} value={question} onChange={(e) => { questionRef.current = e.target.value; setQuestion(e.target.value); setChosen([]); }} placeholder="划选原文后，可在这里改写或补充你的问题。"/><small id="question-help">可直接改写提问；原文引用会保留。</small></label>
        <div className="levels" role="group" aria-label="解释等级">{levels.map((x) => <button key={x} aria-pressed={level === x} onClick={() => setLevel(x)}>{x}</button>)}</div>
        <fieldset><legend>代码来源</legend>
          <select aria-label="来源模式" value={scopeMode} onChange={(e) => changeScope(() => setScopeMode(e.target.value))}>
            <option value="specified_public">指定公开仓库</option><option value="public_search">公开搜索</option><option value="local_authorized">已授权本地仓库</option>
          </select>
          {scopeMode === "local_authorized" ? <><select aria-label="本地句柄" value={localHandle} onChange={(e) => changeScope(() => setLocalHandle(e.target.value))}><option value="">选择已授权仓库</option>{localHandles.map((handle, i) => <option key={handle} value={handle}>本地仓库 {i + 1} · {handle.slice(-6)}</option>)}</select>{!localHandles.length && <p>尚未设置本地仓库。可先留空公开仓库，只学习文档。</p>}</> : <>
            {scopeMode === "specified_public" && <input aria-label="公开仓库" value={repository} onChange={(e) => changeScope(() => setRepository(e.target.value))} placeholder="owner/repo；多个仓库以逗号分隔"/>}
            {scopeMode === "specified_public" && !repository.trim() && <small>留空即可只讲解文档，无需联网。</small>}
            {(scopeMode === "public_search" || repository.trim()) && <label className="check"><input type="checkbox" checked={network} onChange={(e) => changeScope(() => setNetwork(e.target.checked))}/>允许本次联网</label>}
            {scopeMode === "public_search" && <><input aria-label="批准的搜索词" maxLength={500} value={terms} onChange={(e) => changeScope(() => { setTerms(e.target.value); setApproved(false); })} placeholder="只填写通用概念，如 dependency injection"/><label className="check"><input type="checkbox" checked={approved} onChange={(e) => setApproved(e.target.checked)}/>确认发送搜索词</label><small>仅这些词用于公开搜索；课件原文和问题不会发送给 GitHub。</small></>}
          </>}
          <button className="link-button" onClick={() => setAdvanced(!advanced)}>{advanced ? "收起高级选项" : "高级选项"}</button>
          {advanced && <label className="check"><input type="checkbox" checked={compare} onChange={(e) => changeScope(() => setCompare(e.target.checked))}/>比较两个仓库</label>}
        </fieldset>
        <div className="ask-row"><button className="primary" disabled={disabled} onClick={() => ask()}>{busy ? "正在生成…" : "开始讲解"}</button>{busy && <button onClick={cancel}>取消</button>}{explanation && <button disabled={disabled} onClick={() => ask({ followup: true })}>继续追问</button>}</div>
        {result?.status === "NEEDS_SOURCE_SELECTION" && <section className="candidates"><h3>选择候选来源</h3>{result.candidates.map((x) => <label key={x.candidate_id}><input type="checkbox" checked={chosen.includes(x.candidate_id)} onChange={(e) => setChosen((v) => e.target.checked ? [...v, x.candidate_id] : v.filter((i) => i !== x.candidate_id))}/><strong>{x.repository || x.local_handle}</strong><span>{x.file_hint} · {x.ranking_reason}</span></label>)}<button disabled={!chosen.length || busy} onClick={() => ask({ useCandidates: true })}>使用所选来源</button></section>}
        {explanation && <article className="answer">
          <p className="answer-status">{explanation.status === "GROUNDED" ? "含已核验源码" : explanation.status === "FIXTURE" ? "演示回答" : "文档讲解 · 未核验源码"} · {explanation.level}</p>
          {explanation.answer_sections.map((x, i) => <section key={i}><h3>{x.title}</h3><p>{x.text}</p></section>)}
          {explanation.comparison && <section><h3>实现比较</h3><p>{explanation.comparison.summary}</p><ul>{explanation.comparison.tradeoffs.map((t, i) => <li key={i}>{t}</li>)}</ul></section>}
          <details className="citations"><summary>文档依据与概念对应</summary>{explanation.document_citations.map((c, i) => <blockquote key={i}>{c.quote}</blockquote>)}{explanation.concept_code_links.map((link, i) => <p key={i}><strong>{link.concept}</strong>：{link.reason}</p>)}</details>
          {explanation.example_blocks.map((item, index) => <section className="example" key={index}><h3>{item.provenance_kind === "SOURCE_EXACT" ? "已核验原始代码" : item.provenance_kind === "ADAPTED_FROM_SOURCE" ? "基于来源的改编代码" : "AI 生成示例"}</h3><p className="machine-status">{item.execution_status === "NOT_RUN" ? "未运行" : item.execution_status}</p><pre><code>{item.code}</code></pre><p>{item.explanation}</p></section>)}
          {explanation.limitations.length > 0 && <details className="boundary"><summary>范围与局限</summary>{explanation.limitations.map((x, i) => <p key={i}>{x}</p>)}</details>}
          <details className="metrics"><summary>模型与用量</summary><p>{explanation.provider_info.model_id.split(/[\\/]/).filter(Boolean).at(-1)}</p><p>{(explanation.metrics.latency_ms / 1000).toFixed(1)} 秒 · {explanation.metrics.token_source === "PROVIDER_USAGE" ? "模型报告" : "估算"}：输入 {explanation.metrics.input_tokens ?? "未知"} / 输出 {explanation.metrics.output_tokens ?? "未知"} tokens</p>{explanation.metrics.input_truncated && <p>{explanation.metrics.truncation_reason}</p>}</details>
          <label>我的理解<textarea aria-label="我的理解" maxLength={20000} value={noteText} onChange={(e) => setNoteText(e.target.value)} placeholder="这里的文字不会被追问覆盖。"/></label><button disabled={saving} onClick={saveNote}>{saving ? "保存中…" : "保存为笔记"}</button>
        </article>}
      </section>
      <aside className="side pane"><nav aria-label="学习记录"><button aria-pressed={tab === "sources"} onClick={() => setTab("sources")}>来源</button><button aria-pressed={tab === "annotations"} onClick={() => setTab("annotations")}>批注 {annotations.total}</button><button aria-pressed={tab === "notes"} onClick={() => setTab("notes")}>笔记 {notes.length}</button></nav>
        {tab === "sources" ? <div>{!sources.length && <div className="empty"><h3>暂无代码来源</h3><p>加入仓库后，可将文档概念与真实代码联系起来。</p></div>}{sources.map((x) => <SourceCard key={x.source_id} source={x}/>)}</div> : tab === "annotations" ? <Annotations state={annotations} unit={unit} locate={locateAnnotation}/> : <><Notes notes={notes} query={noteQuery} setQuery={setNoteQuery} report={report} changed={(value) => setNotes((items) => items.map((x) => x.note_id === value.note_id ? value : x))} removed={(noteId) => setNotes((items) => items.filter((x) => x.note_id !== noteId))}/>{notes.length < noteTotal && <button onClick={moreNotes}>更多笔记</button>}</>}
      </aside>
    </main>
  </>;
}
