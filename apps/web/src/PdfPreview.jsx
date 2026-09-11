import { useEffect, useRef, useState } from "react";

// Canvas rendering also works in browsers without an embedded PDF plug-in.
export default function PdfPreview({ url, pageIndex }) {
  const canvas = useRef(null), container = useRef(null);
  const [loaded, setLoaded] = useState(null), [error, setError] = useState("");
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
        standardFontDataUrl: "/pdfjs/standard_fonts/", wasmUrl: "/pdfjs/wasm/",
      });
      const document = await task.promise;
      if (live) setLoaded({ url, document });
    })().catch(() => { if (live) setError("页面预览暂不可用，可打开原文件或阅读下方提取文字。"); });
    return () => { live = false; task?.destroy().catch(() => {}); };
  }, [url]);
  useEffect(() => {
    if (!loaded || loaded.url !== url) return;
    let live = true, task;
    setRendered(""); setError("");
    (async () => {
      const page = await loaded.document.getPage(pageIndex);
      if (!live) return;
      const original = page.getViewport({ scale: 1 });
      const scale = Math.min(width * Math.min(window.devicePixelRatio || 1, 2) / original.width,
        4096 / original.width, 4096 / original.height);
      const viewport = page.getViewport({ scale });
      const node = canvas.current;
      node.width = Math.ceil(viewport.width); node.height = Math.ceil(viewport.height);
      task = page.render({ canvas: node, viewport });
      await task.promise;
      if (live) setRendered(key);
    })().catch(() => { if (live) setError("此页预览失败，可打开原文件查看。"); });
    return () => { live = false; task?.cancel(); };
  }, [loaded, url, pageIndex, width, key]);
  return <div className="pdf-canvas-preview" ref={container}>
    {error ? <p role="status">{error}</p> : rendered !== key && <p role="status">正在载入第 {pageIndex} 页…</p>}
    <canvas ref={canvas} role="img" aria-label={`PDF 原始第 ${pageIndex} 页`} hidden={rendered !== key || Boolean(error)}/>
    <a href={url} target="_blank" rel="noreferrer">打开原始 PDF</a>
  </div>;
}
