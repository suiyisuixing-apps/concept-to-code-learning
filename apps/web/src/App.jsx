import { useEffect, useRef, useState } from "react";
import { api, explainStream, hashText, id, json } from "./api.js";
import Reader from "./Reader.jsx";
import ModelPicker from "./ModelPicker.jsx";
import Conversation, { SourceCard } from "./Conversation.jsx";
import Annotations, { useAnnotations } from "./Annotations.jsx";
import { questionForSelection, selectionKey } from "./selection.js";

const levels = { Beginner: "入门", University: "课程", Engineering: "工程", "Source-code": "源码" };
function restoreDraft() { try { return JSON.parse(window.sessionStorage.getItem("c2c-workspace") || "{}"); } catch { return {}; } }
function ErrorBox({ error, retry }) {
  if (!error) return null;
  return <div className="error" role="alert"><span>{error.message}</span>
    {error.retryable && retry && <button onClick={retry}>重试</button>}
    {error.code && <details><summary>详细信息</summary><small>{error.code}</small></details>}</div>;
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
  const draft = useRef(restoreDraft()), restoring = useRef(true);
  const [turns, setTurns] = useState([]), [stage, setStage] = useState("");
  const [model, setModel] = useState(null);
  const [preview, setPreview] = useState([]), [pendingQuestion, setPendingQuestion] = useState("");
  const [, setCaps] = useState(null);
  const [session, setSession] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [record, setRecord] = useState(null);
  const [units, setUnits] = useState([]);
  const [unit, setUnit] = useState(null);
  const [selection, setSelection] = useState(null);
  const [question, setQuestion] = useState(draft.current.question || "");
  const [level, setLevel] = useState(draft.current.level || "Beginner");
  const [scopeMode, setScopeMode] = useState(draft.current.scopeMode || "public_search");
  const [repository, setRepository] = useState(draft.current.repository || "");
  const [localHandles, setLocalHandles] = useState([]);
  const [localHandle, setLocalHandle] = useState("");
  const [terms, setTerms] = useState(draft.current.terms || "");
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
  const [tab, setTab] = useState("chat");
  const [notes, setNotes] = useState([]);
  const [noteQuery, setNoteQuery] = useState("");
  const [noteTotal, setNoteTotal] = useState(0);
  const [noteText, setNoteText] = useState(draft.current.noteText || "");
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
        api("/capabilities"), (async () => {
          let previous;
          try { previous = await api(draft.current.sessionId ? `/sessions/${draft.current.sessionId}` : "/sessions/recent"); } catch { /* A removed session starts afresh. */ }
          return previous?.session_id ? previous : api("/sessions", { method: "POST" });
        })(), api("/documents"),
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
      if (loaded[1].status === "fulfilled" && loaded[2].status === "fulfilled") {
        const previous = loaded[1].value, context = previous.context;
        const doc = loaded[2].value.documents.find((item) => item.document_id === context?.document_id);
        if (doc && context) {
          try {
            const [list, target, history] = await Promise.all([
              api(`/documents/${doc.document_id}/units`), api(`/documents/${doc.document_id}/units/${context.unit_id}`),
              api(`/sessions/${previous.session_id}/history`),
            ]);
            if (!live) return;
            setRecord(doc); setUnits(list.units); setUnit(target);
            setSelection(context.selected_text ? { text: context.selected_text, spans: context.selection_locator?.spans || [] } : null);
            setTurns(Array.isArray(history) ? history : []);
            const latest = Array.isArray(history) ? history.at(-1) : null;
            if (latest?.context_revision === previous.context_revision) setResult(latest);
          } catch (e) { if (live) report(e); }
        } else if (loaded[2].value.documents[0]) await openDocument(loaded[2].value.documents[0]);
      }
      restoring.current = false;
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

  useEffect(() => {
    if (restoring.current || !session) return;
    try { window.sessionStorage.setItem("c2c-workspace", JSON.stringify({ sessionId: session.session_id,
      question, noteText, level, scopeMode, repository, terms })); } catch { /* Storage can be disabled. */ }
  }, [session, question, noteText, level, scopeMode, repository, terms, record]);

  useEffect(() => {
    if (!/^(笔记已保存|批注已保存|批注已删除)/.test(notice)) return;
    const timer = setTimeout(() => setNotice(""), 2200); return () => clearTimeout(timer);
  }, [notice]);

  function stopActive() {
    const pending = active.current;
    active.current = null;
    setBusy(false);
    setPreview([]); setPendingQuestion("");
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
      setTab("chat");
    }
    return next;
  }
  function editQuestion(replace = false) {
    if (replace && selection) { autoQuestion.current = questionForSelection(selection); questionRef.current = autoQuestion.current; setQuestion(autoQuestion.current); }
    questionInput.current?.focus({ preventScroll: true });
    questionInput.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }
  function writeAnnotation() { annotations.start(selection); setTab("annotations"); }
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
    return { source_mode: scopeMode === "document" ? "specified_public" : scopeMode,
      repository_allowlist: scopeMode === "specified_public" ? repos : [],
      local_handle: scopeMode === "local_authorized" ? localHandle || null : null,
      language_hint: null, scope_limit: { repositories: 3, files: 8 },
      network_authorized: scopeMode === "public_search" || scopeMode === "specified_public" && repos.length > 0,
      auto_public_search: scopeMode === "public_search" && !values.length,
      query_terms_approved: values.length > 0, approved_query_terms: values, max_sources: compare ? 2 : 1 };
  }
  async function ask({ followup = true, useCandidates = false } = {}) {
    if (!question.trim() || !session?.context_revision || !sessionRef.current?.context_revision || contextBusy || active.current) return;
    const requestId = id(), current = sessionRef.current, controller = new AbortController();
    const epoch = contextEpoch.current, sentQuestion = question.trim();
    active.current = { requestId, sessionId: current.session_id, controller };
    setBusy(true); setStage("planning"); setError(null); setNotice(""); setPreview([]); setPendingQuestion(sentQuestion);
    try {
      const value = await explainStream({
        request_id: requestId, session_id: current.session_id, context_revision: current.context_revision,
        question: sentQuestion, level, scope: scope(), source_ids: [],
        model_id: model?.id || null, model_base_url: model?.base_url || null,
        candidate_ids: useCandidates ? chosen : [], query_id: useCandidates ? result?.query_id : null,
        compare, continue_from: followup ? explanation?.explanation_id || null : null,
      }, controller.signal, (next) => {
        if (active.current?.requestId !== requestId) return;
        if (next?.type === "preview") setPreview(next.sections); else setStage(next);
      });
      if (active.current?.requestId === requestId && epoch === contextEpoch.current) {
        saveKey.current = null; setResult(value); setChosen([]);
        if (value.explanation) {
          setTurns((items) => [...items, value].slice(-20));
          if (questionRef.current.trim() === sentQuestion) { questionRef.current = ""; autoQuestion.current = ""; setQuestion(""); }
        }
      }
    } catch (e) {
      if (active.current?.requestId === requestId && e.name !== "AbortError") report(e, () => ask({ followup, useCandidates }));
    } finally {
      if (active.current?.requestId === requestId) { active.current = null; setBusy(false); setPreview([]); setPendingQuestion(""); }
    }
  }
  function changeScope(action) { stopActive(); setChosen([]); setResult(null); action(); }
  function cancel() { stopActive(); }
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
      setNotice("笔记已保存");
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
  const disabled = busy || contextBusy || !question.trim() || !session?.context_revision
    || scopeMode === "specified_public" && !repository.trim() || scopeMode === "local_authorized" && !localHandle;
  const stageLabel = { planning: "正在理解问题…", searching: "正在找相关代码…", verifying: "正在核对代码出处…", answering: "正在回答…" }[stage] || "正在回答…";
  return <>
    <header className="topbar">
      <h1>Concept-to-Code</h1>
      <select aria-label="切换文档" value={record?.document_id || ""} onChange={(e) => { const doc = documents.find((x) => x.document_id === e.target.value); if (doc) openDocument(doc); }}>
        <option value="">选择文档</option>{documents.map((x) => <option value={x.document_id} key={x.document_id}>{x.file_name}</option>)}
      </select><span className="local-label">本地工作台</span>
    </header>
    <main className="workspace">
      <Reader record={record} units={units} unit={unit} navigate={(i) => navigate(record, units, i)} select={chooseSelection} selection={selection} importing={importing} importFile={importFile}
        annotations={annotations.highlighted} openAnnotation={openAnnotation} annotate={writeAnnotation} editQuestion={() => editQuestion()} report={report}/>
      <section className="assistant pane" aria-busy={busy || contextBusy}>
        <nav className="chat-tabs" aria-label="学习记录"><button aria-pressed={tab === "chat"} onClick={() => setTab("chat")}>对话</button><button aria-pressed={tab === "annotations"} onClick={() => setTab("annotations")}>批注 {annotations.total}</button><button aria-pressed={tab === "notes"} onClick={() => setTab("notes")}>笔记 {notes.length}</button></nav>
        <ErrorBox error={error} retry={retry.current}/>
        {notice && <p className="notice" role="status">{notice}</p>}
        <div hidden={tab !== "chat"}><ModelPicker change={(value, interactive) => { if (interactive) stopActive(); setModel(value); }} disabled={busy}/></div>
        {tab === "chat" ? <>
          <Conversation turns={turns} current={explanation} noteText={noteText} setNoteText={setNoteText} saving={saving} saveNote={saveNote} preview={preview} pendingQuestion={pendingQuestion}/>
          {result?.status === "NEEDS_SOURCE_SELECTION" && <section className="candidates"><h3>选择代码来源</h3>{result.candidates.map((x) => <label key={x.candidate_id}><input type="checkbox" checked={chosen.includes(x.candidate_id)} onChange={(e) => setChosen((v) => e.target.checked ? [...v, x.candidate_id] : v.filter((i) => i !== x.candidate_id))}/><strong>{x.repository || x.local_handle}</strong><span>{x.file_hint}</span></label>)}<button disabled={!chosen.length || busy} onClick={() => ask({ useCandidates: true })}>使用所选来源</button></section>}
          <div className="composer">
            {selection && <div className="selection-summary"><blockquote>{selection.text}</blockquote><div className="quote-actions"><button onClick={() => editQuestion(true)}>带入问题</button><button disabled={contextBusy} onClick={writeAnnotation}>写批注</button><button disabled={contextBusy} onClick={() => chooseSelection(null)} aria-label="清除引用">取消引用</button></div></div>}
            <textarea ref={questionInput} aria-label="学习问题" maxLength={2000} value={question} onChange={(e) => { questionRef.current = e.target.value; setQuestion(e.target.value); setChosen([]); }} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); if (!disabled) ask(); } }} placeholder="问问这段内容…"/>
            <div className="composer-options">
              <select aria-label="来源模式" value={scopeMode} onChange={(e) => changeScope(() => setScopeMode(e.target.value))}><option value="public_search">GitHub 找代码</option><option value="specified_public">指定仓库</option><option value="local_authorized">本地仓库</option><option value="document">仅文档</option></select>
              <select aria-label="解释等级" value={level} onChange={(e) => { stopActive(); setLevel(e.target.value); }}>{Object.entries(levels).map(([value, name]) => <option key={value} value={value}>{name}</option>)}</select>
              <button className="quiet-button" onClick={() => setAdvanced(!advanced)} aria-expanded={advanced}>搜索设置</button>
              {busy ? <button onClick={cancel}>停止</button> : <button className="primary send" disabled={disabled} onClick={() => ask()}>发送</button>}
            </div>
            {scopeMode === "specified_public" && <input aria-label="公开仓库" value={repository} onChange={(e) => changeScope(() => setRepository(e.target.value))} placeholder="github.com/owner/repo"/>}
            {scopeMode === "local_authorized" && <select aria-label="本地句柄" value={localHandle} onChange={(e) => changeScope(() => setLocalHandle(e.target.value))}><option value="">选择已授权仓库</option>{localHandles.map((handle, i) => <option key={handle} value={handle}>本地仓库 {i + 1} · {handle.slice(-6)}</option>)}</select>}
            {advanced && <div className="search-settings">{scopeMode === "public_search" && <input aria-label="搜索关键词" maxLength={500} value={terms} onChange={(e) => changeScope(() => setTerms(e.target.value))} placeholder="限定关键词（可选）"/>}<label className="check"><input type="checkbox" checked={compare} onChange={(e) => changeScope(() => setCompare(e.target.checked))}/>比较两个仓库</label></div>}
            {busy && <p className="working" role="status">{stageLabel}</p>}
          </div>
        </> : tab === "annotations" ? <Annotations state={annotations} unit={unit} locate={locateAnnotation}/> : <div className="records-panel"><Notes notes={notes} query={noteQuery} setQuery={setNoteQuery} report={report} changed={(value) => setNotes((items) => items.map((x) => x.note_id === value.note_id ? value : x))} removed={(noteId) => setNotes((items) => items.filter((x) => x.note_id !== noteId))}/>{notes.length < noteTotal && <button onClick={moreNotes}>更多笔记</button>}</div>}
      </section>
    </main>
  </>;
}
