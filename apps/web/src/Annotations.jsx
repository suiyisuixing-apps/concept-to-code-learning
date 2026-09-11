import { useEffect, useRef, useState } from "react";
import { api, hashText, id, json } from "./api.js";
import { selectionKey } from "./selection.js";

export function useAnnotations(record, unit, report, notice) {
  const [items, setItems] = useState([]), [total, setTotal] = useState(0), [loading, setLoading] = useState(false);
  const [editor, setEditor] = useState(null), [pending, setPending] = useState(false);
  const epoch = useRef(0), controller = useRef(null), writing = useRef(false), locationRef = useRef(null);
  const location = record && unit ? `${record.document_id}:${unit.unit_id}` : null;
  locationRef.current = location;
  async function load(offset = 0) {
    if (!location) return;
    const current = ++epoch.current;
    controller.current?.abort(); controller.current = new AbortController(); setLoading(true);
    try {
      const value = await api(`/documents/${record.document_id}/annotations?unit_id=${unit.unit_id}&offset=${offset}`, { signal: controller.current.signal });
      if (current !== epoch.current) return;
      const loaded = value.annotations || [];
      setItems((old) => offset ? [...old, ...loaded.filter((a) => !old.some((b) => b.annotation_id === a.annotation_id))] : loaded);
      setTotal(value.total || 0);
    } catch (e) { if (current === epoch.current && e.name !== "AbortError") report(e, () => load(offset)); }
    finally { if (current === epoch.current) setLoading(false); }
  }
  useEffect(() => {
    setItems([]); setTotal(0); load();
    return () => { epoch.current++; controller.current?.abort(); };
  }, [location]);
  const targetKey = (doc, target, value) => `${doc.document_id}:${doc.revision}:${target.unit_id}:${selectionKey(value)}`;
  function start(value, annotation = null) {
    if (!record || !unit || !value || writing.current) return false;
    const key = targetKey(record, unit, value);
    if (editor && (editor.key !== key || editor.annotation?.annotation_id !== annotation?.annotation_id)
        && editor.comment !== editor.original && editor.comment.trim()) {
      notice("当前批注还有未保存的内容。请先保存，或取消编辑后再批注另一处。"); return false;
    }
    if (editor?.key === key && editor.annotation?.annotation_id === annotation?.annotation_id) return true;
    setEditor({ key, record, unit, selection: value, annotation, annotationId: annotation?.annotation_id || id("annotation"),
      comment: annotation?.comment || "", original: annotation?.comment || "" });
    return true;
  }
  function open(annotation) {
    if (annotation.anchor.document_revision !== record?.revision || annotation.anchor.original_sha256 !== record?.original_sha256) {
      notice("这条批注属于另一个文档版本，请核对原文后再引用。"); return false;
    }
    return start({ text: annotation.anchor.selected_text, spans: annotation.anchor.selection_locator.spans }, annotation);
  }
  async function save() {
    if (!editor?.comment.trim() || writing.current) return;
    const value = editor;
    writing.current = true; setPending(true);
    try {
      const saved = value.annotation ? await api(`/annotations/${value.annotation.annotation_id}`, json("PATCH", {
        expected_revision: value.annotation.revision, comment: value.comment,
      })) : await api(`/documents/${value.record.document_id}/annotations`, json("POST", {
        annotation_id: value.annotationId, document_revision: value.record.revision, unit_id: value.unit.unit_id,
        selected_text: value.selection.text, selected_text_hash: await hashText(value.selection.text),
        selection_locator: { spans: value.selection.spans, normalization: "exact" }, comment: value.comment,
      }));
      if (locationRef.current === `${value.record.document_id}:${value.unit.unit_id}`) {
        epoch.current++; controller.current?.abort(); setLoading(false);
        setItems((old) => [saved, ...old.filter((a) => a.annotation_id !== saved.annotation_id)]);
        if (!value.annotation) setTotal((n) => n + 1);
      }
      setEditor(null); notice(`批注已保存 · ${value.record.file_name} · 第 ${value.unit.index} 单元。`);
    } catch (e) { report(e); }
    finally { writing.current = false; setPending(false); }
  }
  async function remove() {
    if (!editor?.annotation || writing.current || !confirm("确认删除这条批注？原文和学习笔记会保留。")) return;
    const value = editor;
    writing.current = true; setPending(true);
    try {
      await api(`/annotations/${value.annotation.annotation_id}`, json("DELETE", {
        expected_revision: value.annotation.revision, confirmed_by_user: true,
      }));
      if (locationRef.current === `${value.record.document_id}:${value.unit.unit_id}`) {
        epoch.current++; controller.current?.abort(); setLoading(false);
        setItems((old) => old.filter((a) => a.annotation_id !== value.annotation.annotation_id)); setTotal((n) => Math.max(0, n - 1));
      }
      setEditor(null); notice("批注已删除。");
    } catch (e) { report(e); }
    finally { writing.current = false; setPending(false); }
  }
  const highlighted = items.filter((a) => a.anchor.document_revision === record?.revision && a.anchor.original_sha256 === record?.original_sha256);
  return { items, highlighted, total, loading, editor, pending, start, open, save, remove,
    update: (comment) => setEditor((old) => old ? { ...old, comment } : old),
    close: () => { if (!writing.current) setEditor(null); }, refresh: () => load(), more: () => { if (!loading) load(items.length); } };
}

export default function Annotations({ state, unit, locate }) {
  const input = useRef(null);
  useEffect(() => { if (state.editor) input.current?.focus(); }, [state.editor?.key]);
  return <section className="annotations" aria-label="文档批注">
    <div className="annotation-heading"><h3>{unit ? `第 ${unit.index} 单元的批注` : "文档批注"}</h3><button disabled={state.loading || !unit} onClick={state.refresh}>刷新批注</button></div>
    {state.editor && <section className="annotation-editor">
      <h3>{state.editor.annotation ? "编辑批注" : "写批注"}</h3>
      <p className="annotation-location">{state.editor.record.file_name} · 第 {state.editor.unit.index} 单元</p>
      <blockquote>{state.editor.selection.text}</blockquote>
      <label>批注内容<textarea ref={input} aria-label="批注内容" value={state.editor.comment} disabled={state.pending} maxLength={20000} onChange={(e) => state.update(e.target.value)} placeholder="写下疑问、理解，或对这段话的改写…"/></label>
      <div className="row"><button className="primary" disabled={state.pending || !state.editor.comment.trim()} onClick={state.save}>{state.pending ? "正在保存批注…" : "保存批注"}</button>
        <button disabled={state.pending} onClick={state.close}>取消编辑</button>{state.editor.annotation && <button className="danger" disabled={state.pending} onClick={state.remove}>删除批注</button>}</div>
      <small>原文作为引用保留，批注只存于本地。</small>
    </section>}
    {state.loading && !state.items.length && <p role="status">正在读取批注…</p>}
    {!state.loading && !state.items.length && <p className="annotation-empty">划选一段文字，点击「写批注」。保存后原文会高亮，重新打开也能找到。</p>}
    <ol className="annotation-list">{state.items.map((item) => <li key={item.annotation_id}>
      <blockquote>{item.anchor.selected_text}</blockquote><p>{item.comment}</p>
      <div className="row"><button disabled={state.pending} onClick={() => locate(item)}>回到原文</button><button disabled={state.pending} onClick={() => state.open(item)}>编辑批注</button><small>修订 {item.revision}</small></div>
    </li>)}</ol>
    {state.items.length < state.total && <button disabled={state.loading} onClick={state.more}>更多批注</button>}
  </section>;
}
