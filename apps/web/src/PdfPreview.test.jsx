import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import PdfPreview from "./PdfPreview.jsx";

const fake = vi.hoisted(() => ({ getDocument: vi.fn(), layers: [], textFailure: false }));
vi.mock("pdfjs-dist/build/pdf.mjs", () => ({ GlobalWorkerOptions: {}, getDocument: fake.getDocument,
  TextLayer: class {
    constructor(options) { this.options = options; this.cancel = vi.fn(); fake.layers.push(this); }
    async render() {
      if (fake.textFailure) throw new Error("text unavailable");
      const span = document.createElement("span"); span.textContent = "Zero  is valid.";
      this.options.container.append(span);
    }
  },
}));
vi.mock("pdfjs-dist/build/pdf.worker.min.mjs?url", () => ({ default: "/worker.mjs" }));
beforeEach(() => {
  vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
  fake.layers.length = 0; fake.textFailure = false;
});

function readyPdf() {
  const page = { getViewport: ({ scale }) => ({ width: 600 * scale, height: 800 * scale, scale }),
    render: vi.fn(() => ({ promise: Promise.resolve(), cancel: vi.fn() })),
    streamTextContent: vi.fn(() => "stream") };
  fake.getDocument.mockReturnValue({ promise: Promise.resolve({ getPage: async () => page }), destroy: vi.fn(async () => {}) });
  return page;
}

test("PDF text selection maps to exact stored text and releases the text layer on exit", async () => {
  const page = readyPdf(), onSelect = vi.fn();
  const view = render(<PdfPreview url="/pdf-3" pageIndex={1} unit={{ blocks: [{ block_id: "b1", text: "Zero is valid." }] }} onSelect={onSelect}/>);
  const text = await screen.findByText("Zero is valid.");
  expect(page.streamTextContent).toHaveBeenCalledWith({ includeMarkedContent: true, disableNormalization: true });
  expect(fake.layers[0].options.viewport.scale).toBe(0.7);
  const range = document.createRange(); range.setStart(text.firstChild, 0); range.setEnd(text.firstChild, 8);
  const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
  fireEvent.mouseDown(text, { button: 0 });
  fireEvent.mouseUp(text, { button: 0 });
  expect(onSelect).toHaveBeenCalledWith({ text: "Zero is", spans: [{ block_id: "b1", start: 0, end: 7 }] });
  view.unmount();
  expect(fake.layers[0].cancel).toHaveBeenCalledOnce();
  selection.removeAllRanges();
});

test("failed PDF text extraction keeps the rendered page with a readable fallback", async () => {
  readyPdf(); fake.textFailure = true;
  render(<PdfPreview url="/pdf-4" pageIndex={1}/>);
  expect(await screen.findByText(/此页暂不支持在页面上划选/)).toBeVisible();
  expect(screen.getByRole("img", { name: "PDF 原始第 1 页" })).toBeVisible();
  expect(screen.getByRole("link", { name: "打开原始 PDF" })).toHaveAttribute("href", "/pdf-4");
});

test("PDF load failure keeps a usable original-file link", async () => {
  fake.getDocument.mockReturnValue({ promise: Promise.reject(new Error("corrupt")), destroy: vi.fn(async () => {}) });
  render(<PdfPreview url="/api/learning/v1/documents/doc-1/assets/original-pdf" pageIndex={1}/>);
  expect(await screen.findByText(/页面预览暂不可用/)).toBeVisible();
  expect(screen.getByRole("link", { name: "打开原始 PDF" })).toHaveAttribute("href", "/api/learning/v1/documents/doc-1/assets/original-pdf");
});

test("leaving a PDF releases its worker and cancels an unfinished page render", async () => {
  const cancel = vi.fn(), destroy = vi.fn(async () => {});
  const page = { getViewport: ({ scale }) => ({ width: 600 * scale, height: 800 * scale }),
    render: vi.fn(() => ({ promise: new Promise(() => {}), cancel })) };
  fake.getDocument.mockReturnValue({ promise: Promise.resolve({ getPage: async () => page }), destroy });
  const view = render(<PdfPreview url="/api/learning/v1/documents/doc-2/assets/original-pdf" pageIndex={1}/>);
  await waitFor(() => expect(page.render).toHaveBeenCalled());
  view.unmount();
  expect(cancel).toHaveBeenCalledOnce();
  expect(destroy).toHaveBeenCalledOnce();
});
