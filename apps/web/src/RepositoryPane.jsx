import { useEffect, useMemo, useRef, useState } from "react";
import { api, json } from "./api.js";
import { captureBlocks, fromSpans } from "./selection.js";

export function Icon({ name, size = 16 }) {
  const paths = { folder: "M3 5h6l2 2h10v12H3z", file: "M6 3h8l4 4v14H6z M14 3v5h4", chevron: "m9 5 7 7-7 7", plus: "M12 5v14M5 12h14", search: "M21 21l-5-5 M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14", code: "m8 6-6 6 6 6m8-12 6 6-6 6m-2-16-4 20", github: "M9 20c-5 1-5-3-7-3m14 6v-4c0-1 .1-2-.7-2.7C19 16 21 14 21 10c0-1.5-.5-3-1.5-4 .2-1.4.1-2.5-.5-4-2 0-3.5 1-4 1.5a13 13 0 0 0-6 0C8.5 3 7 2 5 2c-.6 1.5-.7 2.6-.5 4C3.5 7 3 8.5 3 10c0 4 2 6 5.7 6.3C8 17 8 18 8 19v4", external: "M14 3h7v7m0-7L10 14 M10 3H3v18h18v-7", close: "m6 6 12 12M6 18 18 6", tree: "M5 3v14h5M5 7h5M13 5h7v4h-7zM13 15h7v4h-7z" };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.file}/></svg>;
}

export function codeLink(location) {
  return `https://github.com/${location.repository}/blob/${location.commit_sha}/${location.file_path.split("/").map(encodeURIComponent).join("/")}#L${location.line_start}-L${location.line_end}`;
}

// Token colours preserve the original string; no HTML parsing or code execution.
function Highlight({ text }) {
  return text.split(/("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|#[^\n]*|\/\/[^\n]*|\b(?:def|class|return|import|from|if|else|elif|for|while|in|as|with|raise|try|except|lambda|function|const|let|var|export|new|async|await|public|private|static|void|true|false|None|True|False)\b|\b\d+(?:\.\d+)?\b)/g).map((part, i) => {
    const kind = /^["']/.test(part) ? "string" : /^(#|\/\/)/.test(part) ? "comment" : /^\d/.test(part) ? "number" : /^(def|class|return|import|from|if|else|elif|for|while|in|as|with|raise|try|except|lambda|function|const|let|var|export|new|async|await|public|private|static|void|true|false|None|True|False)$/.test(part) ? "keyword" : "";
    return kind ? <span className={`syntax-${kind}`} key={i}>{part}</span> : part;
  });
}

function FileTree({ repo, directory = "", depth = 0, query = "", activePath, openFile }) {
  const [page, setPage] = useState(null), [error, setError] = useState("");
  const [expanded, setExpanded] = useState(new Set());
  const [retry, setRetry] = useState(0), [loadingMore, setLoadingMore] = useState(false);
  const epoch = useRef(0), loading = useRef(false);
  const url = `/repositories/${repo.repository_id}/tree?directory=${encodeURIComponent(directory)}&q=${encodeURIComponent(query)}`;
  useEffect(() => {
    const generation = ++epoch.current, controller = new AbortController();
    setPage(null); setError(""); loading.current = false; setLoadingMore(false);
    const timer = setTimeout(() => api(url, { signal: controller.signal }).then((value) => {
      if (generation === epoch.current) setPage(value);
    }).catch((e) => { if (generation === epoch.current && e.name !== "AbortError") setError(e.message); }), query ? 180 : 0);
    return () => { clearTimeout(timer); controller.abort(); epoch.current++; };
  }, [url, retry]);
  useEffect(() => {
    if (!activePath || query || directory && !activePath.startsWith(directory + "/")) return;
    const prefix = directory ? directory + "/" : "";
    const remaining = activePath.slice(prefix.length);
    if (remaining.includes("/")) setExpanded((old) => new Set([...old, prefix + remaining.split("/")[0]]));
  }, [activePath, directory, query]);
  async function more() {
    if (loading.current || !page) return;
    loading.current = true; setLoadingMore(true);
    const generation = epoch.current;
    try {
      const next = await api(`${url}&offset=${page.entries.length}`);
      if (generation === epoch.current) setPage((value) => ({ ...next, entries: [...value.entries, ...next.entries] }));
    } catch (e) { if (generation === epoch.current) setError(e.message); }
    finally { if (generation === epoch.current) { loading.current = false; setLoadingMore(false); } }
  }
  function keyboard(event) {
    if (event.target.tagName !== "BUTTON") return;
    const container = event.currentTarget.closest(".repository-tree");
    const rows = [...container.querySelectorAll("button.tree-row")];
    const index = rows.indexOf(event.target);
    const step = event.key === "ArrowDown" ? 1 : event.key === "ArrowUp" ? -1 : 0;
    if (step) { event.preventDefault(); event.stopPropagation(); rows[Math.min(rows.length - 1, Math.max(0, index + step))]?.focus(); }
    if (event.key === "ArrowRight" && event.target.getAttribute("aria-expanded") === "false"
        || event.key === "ArrowLeft" && event.target.getAttribute("aria-expanded") === "true") { event.preventDefault(); event.stopPropagation(); event.target.click(); }
  }
  return <ul className="file-tree" onKeyDown={keyboard} aria-label={directory || `${repo.repository} 文件`}>
    {!page && !error && <li className="tree-message" role="status">读取目录…</li>}
    {error && <li className="tree-message" role="alert">{error}<button onClick={() => setRetry((v) => v + 1)}>重试目录</button></li>}
    {page?.entries.map((entry) => {
      const folder = entry.kind === "folder", isExpanded = expanded.has(entry.path);
      return <li key={entry.path}>
        <button className={`tree-row ${entry.path === activePath ? "is-active" : ""}`} style={{ paddingLeft: `${12 + depth * 14}px` }} title={entry.path}
          aria-expanded={folder ? isExpanded : undefined} aria-current={entry.path === activePath ? "true" : undefined}
          onClick={() => folder ? setExpanded((old) => { const next = new Set(old); if (next.has(entry.path)) next.delete(entry.path); else next.add(entry.path); return next; }) : openFile(repo, entry.path)}>
          <span className={`tree-chevron ${isExpanded ? "is-open" : ""}`}>{folder && <Icon name="chevron" size={12}/>}</span><Icon name={folder ? "folder" : "file"}/><span>{query ? entry.path : entry.path.split("/").at(-1)}</span>{entry.kind === "submodule" && <small>子模块</small>}{entry.kind === "symlink" && <small>链接</small>}
        </button>
        {folder && isExpanded && <FileTree repo={repo} directory={entry.path} depth={depth + 1} activePath={activePath} openFile={openFile}/>}
      </li>;
    })}
    {page && !page.entries.length && <li className="tree-message">{query ? "没有匹配的文件" : "空文件夹"}</li>}
    {page && page.entries.length < page.total && <li><button className="tree-more" disabled={loadingMore} onClick={more}>{loadingMore ? "读取中…" : `更多文件 · 余 ${page.total - page.entries.length}`}</button></li>}
    {query && page && !page.complete_tree && <li className="tree-message">搜索已展开的目录；展开其他文件夹可继续查找。</li>}
  </ul>;
}

function RepositoryImport({ loaded, cancel }) {
  const [value, setValue] = useState(""), [results, setResults] = useState(null), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const active = useRef(false), live = useRef(true);
  useEffect(() => { live.current = true; return () => { live.current = false; }; }, []);
  async function add(repository) {
    if (active.current) return;
    active.current = true; setBusy(true); setError("");
    try { const repo = await api("/repositories", json("POST", { repository })); if (live.current) loaded(repo); }
    catch (e) { if (live.current) setError(e.message); }
    finally { active.current = false; if (live.current) setBusy(false); }
  }
  async function submit(event) {
    event.preventDefault();
    if (!value.trim() || active.current) return;
    if (value.includes("/")) return add(value.trim());
    active.current = true; setBusy(true); setError("");
    try { const items = await api(`/repositories/search?q=${encodeURIComponent(value.trim())}`); if (live.current) setResults(items); }
    catch (e) { if (live.current) setError(e.message); }
    finally { active.current = false; if (live.current) setBusy(false); }
  }
  return <section className="repository-import" aria-label="添加 GitHub 仓库">
    <header><h3>添加代码库</h3><button className="icon-button" aria-label="关闭添加代码库" onClick={cancel}><Icon name="close"/></button></header>
    <form onSubmit={submit}><label htmlFor="repository-address">GitHub 仓库地址或名称</label><div className="repository-input"><input id="repository-address" autoFocus maxLength={300} value={value} onChange={(e) => { setValue(e.target.value); setResults(null); }} placeholder="owner/repo" disabled={busy}/><button className="primary" disabled={busy || !value.trim()}>{busy ? "读取中…" : "添加 / 查找"}</button></div></form>
    <p className="repository-privacy">读取公开仓库，文件保存在本机。</p>
    {error && <p className="inline-error" role="alert">{error}</p>}
    {results && <div className="repository-results">{results.length ? results.map((item) => <button key={item.repository} disabled={busy} onClick={() => add(item.repository)}><strong>{item.repository}</strong><span>{item.description}</span></button>) : <p>没有找到仓库，可粘贴完整地址。</p>}</div>}
  </section>;
}

export default function RepositoryPane({ record, unit, units, selection, select, navigate, openFile, loading, annotations, annotate, repositories, setRepositories, error, resetError }) {
  const [adding, setAdding] = useState(false), [query, setQuery] = useState(""), [treeVisible, setTreeVisible] = useState(true);
  const [collapsed, setCollapsed] = useState(new Set());
  const nodes = useRef(new Map()), anchor = useRef(null), viewport = useRef(null);
  const isCode = record?.source_type === "CODE", origin = isCode ? record.code_location : null;
  const block = isCode ? unit?.blocks[0] : null;
  const lines = useMemo(() => block?.text.split("\n") || [], [block]);
  useEffect(() => { anchor.current = null; if (viewport.current) viewport.current.scrollTop = 0; }, [unit?.unit_id]);
  function selectLine(index, shift) {
    if (!block) return;
    const from = shift && anchor.current !== null ? anchor.current : index;
    if (!shift) anchor.current = index;
    const startLine = Math.min(from, index), endLine = Math.max(from, index);
    const before = lines.slice(0, startLine).join("\n");
    const start = Array.from(before).length + (startLine ? 1 : 0);
    const end = start + Array.from(lines.slice(startLine, endLine + 1).join("\n")).length;
    if (end > start) select(fromSpans(unit, [{ block_id: block.block_id, start, end }]));
  }
  useEffect(() => {
    if (selection?.reveal) viewport.current?.querySelector(".code-line.selected-line")?.scrollIntoView({ block: "center", behavior: "auto" });
  }, [selection, unit?.unit_id]);
  const annotatedLines = new Set();
  for (const annotation of annotations || []) for (const span of annotation.anchor?.selection_locator?.spans || []) {
    if (block && span.block_id === block.block_id) {
      const chars = Array.from(block.text), first = chars.slice(0, span.start).join("").split("\n").length - 1;
      const last = chars.slice(0, span.end).join("").split("\n").length - 1;
      for (let i = first; i <= last; i++) annotatedLines.add(i);
    }
  }
  const selectedLines = new Set();
  for (const span of selection?.spans || []) if (block && span.block_id === block.block_id) {
    const chars = Array.from(block.text);
    const first = chars.slice(0, span.start).join("").split("\n").length - 1;
    const last = chars.slice(0, span.end).join("").split("\n").length - 1;
    for (let i = first; i <= last; i++) selectedLines.add(i);
  }
  const open = (repo, path) => { resetError(); openFile(repo, path); };
  return <section className={`repository-pane pane ${treeVisible ? "" : "tree-hidden"}`} aria-label="代码库工作区" aria-busy={loading}>
    <div className="repository-toolbar"><button className="icon-button" aria-label={treeVisible ? "收起文件树" : "展开文件树"} aria-expanded={treeVisible} onClick={() => setTreeVisible(!treeVisible)}><Icon name="tree"/></button><h2>代码库</h2><span>{repositories.length > 0 ? `${repositories.length} 个仓库` : "GitHub"}</span><button className="add-repository" onClick={() => setAdding(!adding)} aria-expanded={adding}><Icon name="plus"/>添加仓库</button></div>
    {adding && <RepositoryImport cancel={() => setAdding(false)} loaded={(repo) => { setRepositories((old) => [repo, ...old.filter((r) => r.repository_id !== repo.repository_id)]); setAdding(false); setTreeVisible(true); }}/>}
    <div className="repository-body">
      <aside className="repository-tree" hidden={!treeVisible} aria-label="仓库文件夹">
        <label className="tree-search"><Icon name="search" size={14}/><input aria-label="查找仓库文件" maxLength={100} placeholder="查找文件…" value={query} onChange={(e) => setQuery(e.target.value)}/></label>
        {repositories.map((repo) => <div className="repository-root" key={repo.repository_id}>
          <button className="repository-root-button" aria-expanded={!collapsed.has(repo.repository_id)} onClick={() => setCollapsed((old) => { const next = new Set(old); if (next.has(repo.repository_id)) next.delete(repo.repository_id); else next.add(repo.repository_id); return next; })}><Icon name="github"/><span><strong>{repo.repository.split("/")[1]}</strong><small>{repo.repository.split("/")[0]} · {repo.commit_sha.slice(0, 7)}</small></span><span className={`tree-chevron ${!collapsed.has(repo.repository_id) ? "is-open" : ""}`}><Icon name="chevron" size={12}/></span></button>
          {!collapsed.has(repo.repository_id) && <FileTree repo={repo} query={query} activePath={origin?.repository_id === repo.repository_id ? origin.file_path : ""} openFile={open}/>}
        </div>)}
        {!repositories.length && <p className="tree-message">添加的仓库会显示在这里</p>}
      </aside>
      <div className="code-reader">
        {error && <div className="code-read-error" role="alert"><p>{error.message}</p><div><button onClick={error.retry}>重试</button>{error.url && <a href={error.url} target="_blank" rel="noreferrer">在 GitHub 查看 <Icon name="external" size={13}/></a>}<button onClick={resetError}>关闭</button></div></div>}
        {isCode && block ? <>
          <header className="code-file-header"><div><span>{origin.repository}</span><h3 title={origin.file_path}>{origin.file_path}</h3></div><a className="icon-button" aria-label="在 GitHub 打开当前文件" href={codeLink(origin)} target="_blank" rel="noreferrer"><Icon name="external"/></a></header>
          <div className="code-file-meta"><span>{origin.line_end} 行</span><span>{record.code_license?.files.map((f) => f.identifier).filter((v, i, all) => all.indexOf(v) === i).join(" / ")}</span>{units.length > 1 && <select aria-label="代码段" value={unit.unit_id} onChange={(e) => navigate(units.findIndex((u) => u.unit_id === e.target.value))}>{units.map((u) => <option key={u.unit_id} value={u.unit_id}>L{u.blocks[0].code_location.line_start}–{u.blocks[0].code_location.line_end}</option>)}</select>}<span className="code-version">{origin.commit_sha.slice(0, 7)} · 只读</span></div>
          {unit.warnings?.map((warning) => <p className="code-warning" key={warning}>{warning}</p>)}
          <div className="code-viewport" ref={viewport} tabIndex={0} aria-label="源码阅读区" onMouseUp={() => { const value = captureBlocks(unit, nodes.current); if (value) select(value); }} onKeyUp={(e) => { if (e.shiftKey) { const value = captureBlocks(unit, nodes.current); if (value) select(value); } }}>
            <div className="code-grid"><div className="line-numbers" aria-label="选择代码行">{lines.map((_, i) => <button key={i} className={`${selectedLines.has(i) ? "selected-line" : ""} ${annotatedLines.has(i) ? "annotated-line" : ""}`} tabIndex={i === 0 || selectedLines.has(i) ? 0 : -1} aria-label={`选择第 ${block.code_location.line_start + i} 行${annotatedLines.has(i) ? "，有批注" : ""}`} onClick={(e) => selectLine(i, e.shiftKey)} onKeyDown={(e) => { if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); const sibling = e.key === "ArrowDown" ? e.currentTarget.nextElementSibling : e.currentTarget.previousElementSibling; sibling?.focus(); } }}>{block.code_location.line_start + i}</button>)}</div>
              <pre className="code-content"><code ref={(node) => { if (node) nodes.current.set(block.block_id, node); else nodes.current.delete(block.block_id); }}>{lines.map((line, i) => <span className={`code-line ${selectedLines.has(i) ? "selected-line" : ""}`} key={i}><Highlight text={line}/>{i < lines.length - 1 ? "\n" : ""}</span>)}</code></pre>
            </div>
          </div>
          <footer className="code-reader-footer"><span>{selection ? `已选 ${selection.text.split("\n").length} 行` : "选择代码，与 AI 一起理解"}</span>{selection && <button onClick={annotate}>写批注</button>}<span>{annotations?.length > 0 ? `${annotations.length} 条批注` : ""}</span></footer>
        </> : <div className="code-empty"><div className="code-empty-mark"><Icon name="code" size={38}/></div><h3>{repositories.length ? "打开一份代码，开始理解" : "把代码库放在手边"}</h3><p>{repositories.length ? "在左侧选择文件，再向右侧的 AI 提问。" : "加载 GitHub 仓库，沿着目录探索实现。\n从一行代码，到它背后的原理。"}</p>{!repositories.length && <button className="primary" onClick={() => setAdding(true)}><Icon name="plus"/>添加 GitHub 仓库</button>}</div>}
        {loading && <div className="code-loading" role="status"><span className="loading-dot"/>正在读取代码与相关文件…</div>}
      </div>
    </div>
  </section>;
}
