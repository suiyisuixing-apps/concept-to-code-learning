import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import PdfPreview from "./PdfPreview.jsx";

const fake = vi.hoisted(() => ({ getDocument: vi.fn() }));
vi.mock("pdfjs-dist/build/pdf.mjs", () => ({ GlobalWorkerOptions: {}, getDocument: fake.getDocument }));
vi.mock("pdfjs-dist/build/pdf.worker.min.mjs?url", () => ({ default: "/worker.mjs" }));
beforeEach(() => {
  vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
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
