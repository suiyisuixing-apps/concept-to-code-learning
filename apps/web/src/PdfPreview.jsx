import { useEffect, useRef, useState } from "react";
import { capturePdf } from "./selection.js";

// Canvas rendering also works in browsers without an embedded PDF plug-in.
export default function PdfPreview({ url, pageIndex, unit, onSelect, report }) {
  const canvas = useRef(null), container = useRef(null), layer = useRef(null), pageFrame = useRef(null);
  const dragging = useRef(false);
  const selectionProps = useRef(null); selectionProps.current = { unit, onSelect, report };
  const [loaded, setLoaded] = useState(null), [error, setError] = useState("");
  const [textError, setTextError] = useState("");
  const [width, setWidth] = useState(420), [rendered, setRendered] = useState("");
  const key = `${url}:${pageIndex}:${width}`;
  useEffect(() => {
    const measure = () => setWidth(Math.max(200, Math.floor(container.current?.clientWidth || 420)));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    let live = true, task;
    setError(""); setLoaded(null);
    (async () => {
      const pdfjs = await import("pdfjs-dist/build/pdf.mjs");
      const worker = await import("pdfjs-dist/build/pdf.worker.min.mjs?url");
      if (!live) return;
      pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
      task = pdfjs.getDocument({
        url, isEvalSupported: false, enableXfa: false,
        cMapUrl: "/pdfjs/cmaps/", cMapPacked: true,
        iccUrl: "/pdfjs/iccs/",
        standardFontDataUrl: "/pdfjs/standard_fonts/", wasmUrl: "/pdfjs/wasm/",
      });
      const document = await task.promise;
      if (live) setLoaded({ url, document, pdfjs });
    })().catch(() => { if (live) setError("页面预览暂不可用，可打开原文件或阅读下方提取文字。"); });
    return () => { live = false; task?.destroy().catch(() => {}); };
  }, [url]);
  useEffect(() => {
    if (!loaded || loaded.url !== url) return;
    let live = true, task, textTask;
    setRendered(""); setError(""); setTextError("");
    (async () => {
      const page = await loaded.document.getPage(pageIndex);
      if (!live) return;
      const original = page.getViewport({ scale: 1 });
      const viewport = page.getViewport({ scale: width / original.width });
      const ratio = Math.min(window.devicePixelRatio || 1, 2, 4096 / viewport.width, 4096 / viewport.height);
      const node = canvas.current;
      node.width = Math.ceil(viewport.width * ratio); node.height = Math.ceil(viewport.height * ratio);
      pageFrame.current.style.height = `${viewport.height}px`;
      layer.current.replaceChildren();
      layer.current.style.setProperty("--total-scale-factor", String(viewport.scale));
      task = page.render({ canvas: node, viewport, transform: [ratio, 0, 0, ratio, 0, 0] });
      await task.promise;
      if (!live) return;
      setRendered(key);
      try {
        textTask = new loaded.pdfjs.TextLayer({ textContentSource: page.streamTextContent({ includeMarkedContent: true, disableNormalization: true }), container: layer.current, viewport });
        await textTask.render();
      } catch { if (live) setTextError("此页暂不支持在页面上划选，可在下方提取文字中选择。"); }
    })().catch(() => { if (live) setError("此页预览失败，可打开原文件查看。"); });
    return () => { live = false; task?.cancel(); textTask?.cancel(); };
  }, [loaded, url, pageIndex, width, key]);
  function selectText() {
    const current = selectionProps.current;
    const selection = window.getSelection();
    if (!current.unit || !selection?.rangeCount || selection.isCollapsed || !layer.current?.contains(selection.anchorNode)
        || !layer.current.contains(selection.focusNode)) return;
    const value = capturePdf(current.unit, layer.current, selection);
    if (value) current.onSelect?.(value);
    else current.report?.(new Error("这段 PDF 文字暂时无法准确定位，请从下方提取文字中划选。"));
  }
  const capture = useRef(null); capture.current = selectText;
  useEffect(() => {
    const up = (event) => {
      if (event.button !== 0 || !dragging.current) return;
      dragging.current = false; capture.current?.();
    };
    document.addEventListener("mouseup", up);
    return () => document.removeEventListener("mouseup", up);
  }, []);
  return <div className="pdf-canvas-preview" ref={container}>
    {error ? <p role="status">{error}</p> : rendered !== key && <p role="status">正在载入第 {pageIndex} 页…</p>}
    <div className="pdf-page" ref={pageFrame} hidden={rendered !== key || Boolean(error)}>
      <canvas ref={canvas} role="img" aria-label={`PDF 原始第 ${pageIndex} 页`}/>
      <div className="pdf-text-layer" ref={layer} onMouseDown={(e) => { if (e.button === 0) dragging.current = true; }} onKeyUp={selectText} aria-label={`PDF 第 ${pageIndex} 页可选文字`}/>
    </div>
    {textError && <p role="status">{textError}</p>}
    <a href={url} target="_blank" rel="noreferrer">打开原始 PDF</a>
  </div>;
}
