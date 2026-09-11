import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { assetUrl } from "./api.js";
import { captureBlocks, selectionKey } from "./selection.js";
import PdfPreview from "./PdfPreview.jsx";

function MarkedText({ block, selection, annotations, openAnnotation }) {
  const chars = Array.from(block.text), ranges = [];
  for (const item of annotations) for (const span of item.anchor.selection_locator.spans) {
    if (span.block_id === block.block_id) ranges.push({ ...span, annotation: item });
  }
  for (const span of selection?.spans || []) if (span.block_id === block.block_id) ranges.push({ ...span, active: true });
  const points = [...new Set([0, chars.length, ...ranges.flatMap((r) => [r.start, r.end])])]
    .filter((n) => n >= 0 && n <= chars.length).sort((a, b) => a - b);
  return points.slice(0, -1).map((start, i) => {
    const end = points[i + 1], text = chars.slice(start, end).join("");
    const covering = ranges.filter((r) => r.start <= start && r.end >= end);
    if (!covering.length) return text;
    const saved = covering.find((r) => r.annotation)?.annotation;
    const active = covering.some((r) => r.active);
    return <mark key={start} className={active ? "quoted-text" : "annotated-text"}
      title={saved?.comment} role={saved ? "button" : undefined} tabIndex={saved ? 0 : undefined}
      aria-label={saved ? `查看批注：${saved.comment.slice(0, 60)}` : undefined}
      onClick={() => { if (saved && window.getSelection()?.isCollapsed) openAnnotation(saved); }}
      onKeyDown={(e) => { if (saved && ["Enter", " "].includes(e.key)) { e.preventDefault(); openAnnotation(saved); } }}>{text}</mark>;
  });
}

export default function Reader({ record, units, unit, navigate, select, selection, importing, importFile,
  annotations, openAnnotation, annotate, editQuestion, report }) {
  const nodes = useRef(new Map()), dragging = useRef(false);
  const [search, setSearch] = useState(""), [toolbar, setToolbar] = useState(null);
  const [textOpen, setTextOpen] = useState(false);
  const latest = useRef(null);
  const location = `${record?.document_id}:${unit?.unit_id}`;
  const matches = unit?.blocks.filter((item) => search.trim() && item.text.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase())) || [];
  function accept(value, showToolbar = true) {
    if (!value?.text.trim()) return;
    const range = window.getSelection()?.rangeCount ? window.getSelection().getRangeAt(0) : null;
    const rect = range?.getBoundingClientRect?.();
    if (showToolbar && rect && (rect.width || rect.height)) setToolbar({ key: selectionKey(value),
      left: Math.max(12, Math.min(rect.left, window.innerWidth - 276)),
      top: rect.bottom + 52 < window.innerHeight ? rect.bottom + 8 : Math.max(8, rect.top - 48) });
    else setToolbar(null);
    select(value);
  }
  function capture() { if (unit) accept(captureBlocks(unit, nodes.current)); }
  latest.current = capture;
  useEffect(() => {
    setToolbar(null); setSearch(""); setTextOpen(false);
  }, [location]);
  useEffect(() => {
    // Capture a user gesture once. Rendering marks can itself change the native
    // Range; that DOM update must never be mistaken for a new user selection.
    const up = (event) => {
      if (event.button !== 0 || !dragging.current) return;
      dragging.current = false; latest.current?.();
    };
    document.addEventListener("mouseup", up);
    return () => document.removeEventListener("mouseup", up);
  }, []);
  useEffect(() => {
    const span = selection?.spans?.[0];
    if (selection?.reveal && span) {
      setTextOpen(true);
      if (textOpen || unit?.preview.kind !== "native_pdf") nodes.current.get(span.block_id)?.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [selection, textOpen]);
  const whole = (item) => accept({ text: item.text, spans: [{ block_id: item.block_id, start: 0, end: Array.from(item.text).length }] }, false);
  return <section className="reader pane" onScroll={() => setToolbar(null)}>
    <div className="pane-header"><h2>{record?.file_name || "导入学习材料"}</h2><label className="import">
      <input aria-label="导入文件" disabled={importing} type="file" accept=".pdf,.pptx,.docx,.md,.markdown" onChange={(e) => { const file = e.target.files[0]; if (file) importFile(file); e.target.value = ""; }}/>{importing ? "导入中…" : "导入文件"}</label></div>
    {!record ? <div className="empty"><h3>选择 PDF、PPTX、DOCX 或 Markdown</h3><p>文件副本与提取结果只保存在本地数据目录。</p></div> : <>
      <div className="doc-meta"><span>{record.unit_count} {record.source_type === "PDF" ? "页" : "个单元"}</span></div>
      <nav className="unit-nav" aria-label="文档导航"><button aria-label="上一单元" disabled={!unit || unit.index === 1} onClick={() => navigate(unit.index - 2)}>←</button>
        <select aria-label="当前页或章节" value={unit?.unit_id || ""} onChange={(e) => navigate(units.findIndex((x) => x.unit_id === e.target.value))}>{units.map((x) => <option key={x.unit_id} value={x.unit_id}>{x.index}. {x.heading_path.at(-1) || x.unit_type}</option>)}</select>
        <button aria-label="下一单元" disabled={!unit || unit.index === units.length} onClick={() => navigate(unit.index)}>→</button></nav>
      <div className="block-search"><input aria-label="搜索当前单元" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="搜索当前页或章节"/>{search && <span>{matches.length} 个匹配块</span>}</div>
      {matches.length > 0 && <div className="search-results">{matches.map((item) => <button key={item.block_id} onClick={() => whole(item)}>选择：{item.text.slice(0, 48)}</button>)}</div>}
      {unit?.preview.kind === "native_pdf" && <PdfPreview url={assetUrl(record.document_id, unit.preview.asset_id)} pageIndex={unit.index} unit={unit} onSelect={accept} report={(e) => { setTextOpen(true); report(e); }}/>}
      {record.source_type !== "MARKDOWN" && unit?.preview.limitations?.length > 0 && <details className="document-info"><summary>文档信息</summary><p>{unit.preview.limitations.join(" ")}</p></details>}
      {unit?.preview.kind === "native_pdf" && <button className="text-toggle" aria-expanded={textOpen} onClick={() => setTextOpen(!textOpen)}>{textOpen ? "收起文字" : "查看文字与批注"}</button>}
      <article hidden={unit?.preview.kind === "native_pdf" && !textOpen} className="blocks" tabIndex="0" onMouseDown={(e) => { if (e.button === 0) dragging.current = true; }} onKeyUp={capture} aria-label="当前文档单元">
        {unit?.heading_path.length > 0 && unit.blocks[0]?.text !== unit.heading_path.at(-1) && <h3>{unit.heading_path.join(" / ")}</h3>}
        {unit?.blocks.map((item, i) => <div className="reading-block" key={item.block_id}>
          {item.kind === "table" ? <div className="table-wrap"><table><tbody>{item.table_rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>)}</tbody></table><button onClick={() => whole(item)}>选中表格</button></div>
            : item.image_asset_id ? <img src={assetUrl(record.document_id, item.image_asset_id)} alt="文档内图片"/>
            : item.kind === "unsupported" ? <p className="boundary">此对象无法完整呈现，请参照原文件。</p>
            : <><div data-block-id={item.block_id} ref={(node) => node ? nodes.current.set(item.block_id, node) : nodes.current.delete(item.block_id)}>
              {item.kind === "code" ? <pre><code><MarkedText block={item} selection={selection} annotations={annotations} openAnnotation={openAnnotation}/></code></pre>
                : <p className={item.text === unit.heading_path.at(-1) ? "document-heading" : undefined}><MarkedText block={item} selection={selection} annotations={annotations} openAnnotation={openAnnotation}/></p>}
            </div>{item.text.trim() && <button className="select-block" aria-label={`选择整段 ${i + 1}`} onClick={() => whole(item)}>选整段</button>}</>}
        </div>)}
        {unit?.extraction_status === "NO_EXTRACTABLE_TEXT" && <div className="empty"><strong>NO_EXTRACTABLE_TEXT</strong><p>没有可提取文字；原始页面或图片仍保留。</p></div>}
      </article>
    </>}
    {toolbar && selection && toolbar.key === selectionKey(selection) && createPortal(<div className="selection-toolbar" role="toolbar" aria-label="选区快捷操作" style={{ left: toolbar.left, top: toolbar.top }}>
      <button onClick={() => { setToolbar(null); editQuestion(); }}>编辑提问</button><button onClick={() => { setToolbar(null); annotate(); }}>添加批注</button>
      <button aria-label="收起选区工具" onClick={() => setToolbar(null)}>收起</button></div>, document.body)}
  </section>;
}
